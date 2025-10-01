import time, os, math, json, hashlib
from typing import List, Dict, Tuple
import numpy as np
from .settings import settings
from .ingest import chunk_text, doc_hash
from qdrant_client import QdrantClient, models as qm

# ---- Simple local embedder (deterministic) ----
def _tokenize(s: str) -> List[str]:
    return [t.lower() for t in s.split()]

class SemanticEmbedder:
    def __init__(self, dim: int = 384):
        self.dim = dim
        try:
            from sentence_transformers import SentenceTransformer
            # Use a lightweight but effective model
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Loaded Sentence-Transformers semantic embedder")
            self.use_semantic = True
        except ImportError:
            print("⚠️  Sentence-Transformers not available, falling back to hash-based embedder")
            self.use_semantic = False

    def embed(self, text: str) -> np.ndarray:
        if self.use_semantic:
            # Use real semantic embeddings
            embedding = self.model.encode(text, convert_to_numpy=True)
            # Ensure consistent dimensionality
            if len(embedding) != self.dim:
                if len(embedding) > self.dim:
                    # Truncate
                    embedding = embedding[:self.dim]
                else:
                    # Pad with zeros
                    padded = np.zeros(self.dim, dtype=np.float32)
                    padded[:len(embedding)] = embedding
                    embedding = padded
            return embedding.astype(np.float32)
        else:
            # Fallback to simple hash-based (for compatibility)
            h = hashlib.sha1(text.encode("utf-8")).digest()
            rng_seed = int.from_bytes(h[:8], "big") % (2**32-1)
            rng = np.random.default_rng(rng_seed)
            v = rng.standard_normal(self.dim).astype("float32")
            v = v / (np.linalg.norm(v) + 1e-9)
            return v

class LocalEmbedder(SemanticEmbedder):
    """Backward compatibility alias"""
    pass

# ---- Vector store abstraction ----
class InMemoryStore:
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vecs: List[np.ndarray] = []
        self.meta: List[Dict] = []
        self._hashes = set()

    def upsert(self, vectors: List[np.ndarray], metadatas: List[Dict]):
        for v, m in zip(vectors, metadatas):
            self.vectors.append(v)
            self.metadatas.append(m)

    def count(self) -> int:
        """Get actual count of vectors in memory"""
        return len(self.vectors)

    def search(self, query: np.ndarray, k: int = 4) -> List[Tuple[float, Dict]]:
        if not self.vecs:
            return []
        A = np.vstack(self.vecs)  # [N, d]
        q = query.reshape(1, -1)  # [1, d]
        # cosine similarity
        sims = (A @ q.T).ravel() / (np.linalg.norm(A, axis=1) * (np.linalg.norm(q) + 1e-9) + 1e-9)
        idx = np.argsort(-sims)[:k]
        return [(float(sims[i]), self.meta[i]) for i in idx]

class QdrantStore:
    def __init__(self, collection: str, dim: int = 384):
        self.client = QdrantClient(url="http://qdrant:6333", timeout=10.0)
        self.collection = collection
        self.dim = dim
        self._ensure_collection()

    def _ensure_collection(self):
        try:
            self.client.get_collection(self.collection)
        except Exception:
            self.client.recreate_collection(
                collection_name=self.collection,
                vectors_config=qm.VectorParams(size=self.dim, distance=qm.Distance.COSINE)
            )

    def upsert(self, vectors: List[np.ndarray], metadatas: List[Dict]):
        points = []
        for i, (v, m) in enumerate(zip(vectors, metadatas)):
            # Convert hash string to integer for Qdrant compatibility
            point_id = i
            if m.get("hash"):
                # Convert hex hash to integer (take first 8 bytes to avoid overflow)
                point_id = int(m["hash"][:16], 16)
            elif m.get("id"):
                point_id = m["id"] if isinstance(m["id"], int) else i
            
            points.append(qm.PointStruct(id=point_id, vector=v.tolist(), payload=m))
        self.client.upsert(collection_name=self.collection, points=points)

    def count(self) -> int:
        """Get actual count of vectors in the collection"""
        try:
            info = self.client.get_collection(self.collection)
            return info.points_count
        except Exception:
            return 0

    def search(self, query: np.ndarray, k: int = 4) -> List[Tuple[float, Dict]]:
        res = self.client.search(
            collection_name=self.collection,
            query_vector=query.tolist(),
            limit=k,
            with_payload=True
        )
        out = []
        for r in res:
            out.append((float(r.score), dict(r.payload)))
        return out

# ---- LLM provider ----
class StubLLM:
    def generate(self, query: str, contexts: List[Dict]) -> str:
        lines = [f"Answer (stub): Based on the following sources:"]
        for c in contexts:
            sec = c.get("section") or "Section"
            lines.append(f"- {c.get('title')} — {sec}")
        lines.append("Summary:")
        # naive summary of top contexts
        joined = " ".join([c.get("text", "") for c in contexts])
        lines.append(joined[:600] + ("..." if len(joined) > 600 else ""))
        return "\n".join(lines)

class OpenAILLM:
    def __init__(self, api_key: str):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

    def generate(self, query: str, contexts: List[Dict]) -> str:
        try:
            prompt = f"You are a helpful company policy assistant. Cite sources by title and section when relevant.\nQuestion: {query}\nSources:\n"
            for c in contexts:
                prompt += f"- {c.get('title')} | {c.get('section')}\n{c.get('text')[:600]}\n---\n"
            prompt += "Write a concise, accurate answer grounded in the sources. If unsure, say so."
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                temperature=0.1
            )
            return resp.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                return "❌ OpenAI API authentication failed. Please check your API key in the .env file."
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                return "❌ OpenAI API quota exceeded. Please check your usage limits."
            else:
                return f"❌ OpenAI API error: {error_msg[:100]}..."

class OllamaLLM:
    def __init__(self, host: str = "http://localhost:11434"):
        import httpx
        self.host = host.rstrip('/')
        self.client = httpx.Client(timeout=120.0)
        
    def generate(self, query: str, contexts: List[Dict]) -> str:
        try:
            prompt = f"You are a helpful company policy assistant. Cite sources by title and section when relevant.\nQuestion: {query}\nSources:\n"
            for c in contexts:
                prompt += f"- {c.get('title')} | {c.get('section')}\n{c.get('text')[:600]}\n---\n"
            prompt += "Write a concise, accurate answer grounded in the sources. If unsure, say so."
            
            payload = {
                "model": "llama3.2:1b",  # Lightweight model
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500
                }
            }
            
            response = self.client.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "Sorry, I couldn't generate a response.")
        except Exception as e:
            error_msg = str(e)
            if "connection" in error_msg.lower() or "refused" in error_msg.lower():
                return "❌ Cannot connect to Ollama. Please ensure Ollama is running and accessible."
            elif "timeout" in error_msg.lower():
                return "❌ Ollama request timed out. The model may be loading or overloaded."
            elif "404" in error_msg:
                return "❌ Ollama model 'llama3.2:1b' not found. Please pull the model: `ollama pull llama3.2:1b`"
            else:
                return f"❌ Ollama error: {error_msg[:100]}..."

# ---- RAG Orchestrator & Metrics ----
class Metrics:
    def __init__(self):
        self.t_retrieval = []
        self.t_generation = []

    def add_retrieval(self, ms: float):
        self.t_retrieval.append(ms)

    def add_generation(self, ms: float):
        self.t_generation.append(ms)

    def summary(self) -> Dict:
        avg_r = sum(self.t_retrieval)/len(self.t_retrieval) if self.t_retrieval else 0.0
        avg_g = sum(self.t_generation)/len(self.t_generation) if self.t_generation else 0.0
        return {
            "avg_retrieval_latency_ms": round(avg_r, 2),
            "avg_generation_latency_ms": round(avg_g, 2),
        }

class RAGEngine:
    def __init__(self):
        self.embedder = LocalEmbedder(dim=384)
        # Vector store selection
        if settings.vector_store == "qdrant":
            try:
                self.store = QdrantStore(collection=settings.collection_name, dim=384)
            except Exception:
                self.store = InMemoryStore(dim=384)
        else:
            self.store = InMemoryStore(dim=384)

        # LLM selection with better error handling
        self.llm_name = "stub"  # Default fallback
        
        if settings.llm_provider == "openai" and settings.openai_api_key:
            try:
                # Validate API key format
                if not settings.openai_api_key.startswith(('sk-', 'sk-proj-')):
                    print(f"⚠️  Invalid OpenAI API key format. Using stub LLM.")
                    self.llm = StubLLM()
                else:
                    self.llm = OpenAILLM(api_key=settings.openai_api_key)
                    self.llm_name = "openai:gpt-4o-mini"
                    print(f"✅ Initialized OpenAI LLM")
            except Exception as e:
                print(f"⚠️  Failed to initialize OpenAI LLM: {e}. Using stub LLM.")
                self.llm = StubLLM()
                self.llm_name = "stub"
        elif settings.llm_provider == "ollama":
            try:
                self.llm = OllamaLLM(host=settings.ollama_host)
                self.llm_name = "ollama:llama3.2:1b"
                print(f"✅ Initialized Ollama LLM at {settings.ollama_host}")
            except Exception as e:
                print(f"⚠️  Failed to initialize Ollama LLM: {e}. Using stub LLM.")
                self.llm = StubLLM()
                self.llm_name = "stub"
        else:
            self.llm = StubLLM()
            self.llm_name = "stub"
            print(f"✅ Using stub LLM (provider: {settings.llm_provider})")
            
        # Add LLM health check
        self._llm_healthy = self._check_llm_health()

        self.metrics = Metrics()
        self._doc_titles = set()
        self._chunk_count = 0
        
        # Sync with existing data on startup
        self._sync_with_existing_data()

    def _check_llm_health(self) -> bool:
        """Quick health check for the LLM"""
        try:
            if isinstance(self.llm, StubLLM):
                return True  # Stub is always healthy
            
            # Quick test generation
            test_response = self.llm.generate("Test", [{"title": "Test", "section": "Test", "text": "Test"}])
            return not test_response.startswith("❌")
        except Exception:
            return False

    def _sync_with_existing_data(self):
        """Sync internal counters with existing data in the vector store"""
        try:
            if isinstance(self.store, QdrantStore):
                # Get collection info from Qdrant
                collection_info = self.store.client.get_collection(self.store.collection)
                self._chunk_count = collection_info.points_count
                
                # Get unique document titles from existing data
                # Scroll through all points to get document titles
                points = self.store.client.scroll(
                    collection_name=self.store.collection,
                    limit=1000,  # Adjust if you have more than 1000 chunks
                    with_payload=True
                )
                
                for point in points[0]:  # points[0] contains the actual points
                    if point.payload and "title" in point.payload:
                        self._doc_titles.add(point.payload["title"])
                        
            elif isinstance(self.store, InMemoryStore):
                # For in-memory store, count existing data
                self._chunk_count = len(self.store.vecs)
                for meta in self.store.meta:
                    if "title" in meta:
                        self._doc_titles.add(meta["title"])
                        
        except Exception as e:
            # If sync fails (e.g., collection doesn't exist), start with empty counters
            self._doc_titles = set()
            self._chunk_count = 0

    def ingest_chunks(self, chunks: List[Dict]) -> Tuple[int, int]:
        vectors = []
        metas = []
        doc_titles_before = set(self._doc_titles)
        processed_hashes = set()
        chunks_before = self.store.count()

        for ch in chunks:
            text = ch["text"]
            h = doc_hash(text)
            
            # Skip if we already processed this exact chunk in this batch
            if h in processed_hashes:
                continue
                
            meta = {
                "id": h,
                "hash": h,
                "title": ch["title"],
                "section": ch.get("section"),
                "text": text,
            }
            v = self.embedder.embed(text)
            vectors.append(v)
            metas.append(meta)
            processed_hashes.add(h)
            self._doc_titles.add(ch["title"])

        if vectors:
            self.store.upsert(vectors, metas)
            
        # Return actual counts: new docs and chunks added
        new_docs = len(self._doc_titles) - len(doc_titles_before)
        chunks_after = self.store.count()
        new_chunks = chunks_after - chunks_before
            
        return (new_docs, max(0, new_chunks))  # Ensure non-negative

    def retrieve(self, query: str, k: int = 4) -> List[Dict]:
        t0 = time.time()
        qv = self.embedder.embed(query)
        results = self.store.search(qv, k=k)
        self.metrics.add_retrieval((time.time()-t0)*1000.0)
        return [meta for score, meta in results]

    def generate(self, query: str, contexts: List[Dict]) -> str:
        t0 = time.time()
        answer = self.llm.generate(query, contexts)
        self.metrics.add_generation((time.time()-t0)*1000.0)
        return answer

    def stats(self) -> Dict:
        m = self.metrics.summary()
        return {
            "total_docs": len(self._doc_titles),
            "total_chunks": self.store.count(),  # Get actual count from store
            "embedding_model": settings.embedding_model,
            "llm_model": self.llm_name,
            "llm_healthy": self._llm_healthy,
            "vector_store": settings.vector_store,
            **m
        }

# ---- Helpers ----
def build_chunks_from_docs(docs: List[Dict], chunk_size: int, overlap: int) -> List[Dict]:
    out = []
    for d in docs:
        for ch in chunk_text(d["text"], chunk_size, overlap):
            out.append({"title": d["title"], "section": d["section"], "text": ch})
    return out
