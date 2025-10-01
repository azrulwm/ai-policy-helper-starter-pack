from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List
from .models import IngestResponse, AskRequest, AskResponse, MetricsResponse, Citation, Chunk
from .settings import settings
from .ingest import load_documents
from .rag import RAGEngine, build_chunks_from_docs

app = FastAPI(title="AI Policy & Product Helper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = RAGEngine()

@app.get("/api/health")
def health():
    config_status = settings.validate_config()
    return {
        "status": "ok",
        "config_valid": config_status["valid"],
        "config_issues": config_status["issues"],
        "config_warnings": config_status["warnings"],
        "llm_provider": settings.llm_provider,
        "vector_store": settings.vector_store
    }

@app.get("/api/metrics", response_model=MetricsResponse)
def metrics():
    s = engine.stats()
    return MetricsResponse(**s)

@app.post("/api/ingest", response_model=IngestResponse)
def ingest():
    docs = load_documents(settings.data_dir)
    chunks = build_chunks_from_docs(docs, settings.chunk_size, settings.chunk_overlap)
    new_docs, new_chunks = engine.ingest_chunks(chunks)
    return IngestResponse(indexed_docs=new_docs, indexed_chunks=new_chunks)

@app.post("/api/ask", response_model=AskResponse)
def ask(req: AskRequest):
    # Check if documents have been ingested
    stats = engine.stats()
    if stats["total_docs"] == 0:
        return AskResponse(
            query=req.query,
            answer="⚠️ No documents have been ingested yet. Please use the Admin panel to 'Ingest sample docs' first, then try asking your question.",
            citations=[],
            chunks=[],
            metrics={
                "retrieval_ms": 0.0,
                "generation_ms": 0.0,
            }
        )
    
    ctx = engine.retrieve(req.query, k=req.k or 4)
    answer = engine.generate(req.query, ctx)
    citations = [Citation(title=c.get("title"), section=c.get("section")) for c in ctx]
    chunks = [Chunk(title=c.get("title"), section=c.get("section"), text=c.get("text")) for c in ctx]
    return AskResponse(
        query=req.query,
        answer=answer,
        citations=citations,
        chunks=chunks,
        metrics={
            "retrieval_ms": stats["avg_retrieval_latency_ms"],
            "generation_ms": stats["avg_generation_latency_ms"],
        }
    )
