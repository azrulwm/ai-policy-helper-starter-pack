from pydantic import BaseModel
import os

class Settings(BaseModel):
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "local-384")
    llm_provider: str = os.getenv("LLM_PROVIDER", "stub")  # stub | openai | ollama
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    vector_store: str = os.getenv("VECTOR_STORE", "qdrant")  # qdrant | memory
    collection_name: str = os.getenv("COLLECTION_NAME", "policy_helper")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "700"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "80"))
    data_dir: str = os.getenv("DATA_DIR", "/app/data")

    def validate_config(self) -> dict:
        """Validate configuration and return status"""
        issues = []
        warnings = []
        
        # Validate LLM provider configuration
        if self.llm_provider == "openai":
            if not self.openai_api_key:
                issues.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            elif not self.openai_api_key.startswith(('sk-', 'sk-proj-')):
                issues.append("OPENAI_API_KEY appears to have invalid format")
        
        if self.llm_provider == "ollama":
            if not self.ollama_host:
                issues.append("OLLAMA_HOST is required when LLM_PROVIDER=ollama")
        
        # Validate chunk settings
        if self.chunk_size < 100:
            warnings.append("CHUNK_SIZE is very small, may affect retrieval quality")
        if self.chunk_overlap >= self.chunk_size:
            issues.append("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
            
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }

settings = Settings()

# Print configuration validation on startup
config_status = settings.validate_config()
if config_status["issues"]:
    print("❌ Configuration Issues:")
    for issue in config_status["issues"]:
        print(f"   • {issue}")
if config_status["warnings"]:
    print("⚠️  Configuration Warnings:")
    for warning in config_status["warnings"]:
        print(f"   • {warning}")
if config_status["valid"] and not config_status["warnings"]:
    print("✅ Configuration validated successfully")
