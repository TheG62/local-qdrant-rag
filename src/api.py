"""OpenAI-compatible API server for Local Qdrant RAG.

This module provides a REST API that mimics the OpenAI Chat Completions API,
allowing integration with tools like OpenWebUI, Continue.dev, etc.

Usage:
    python -m uvicorn src.api:app --host 0.0.0.0 --port 8000
    
Or via CLI:
    python -m src.cli serve
"""

import logging
import time
import uuid
from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import json

from .retrieval import get_retrieval_strategy
from .providers import OllamaProvider
from .settings import settings
from .vectorstore import get_qdrant_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI(
    title="Local Qdrant RAG API",
    description="OpenAI-kompatible API für lokales RAG mit Qdrant und Ollama",
    version="1.0.0",
)

# CORS für OpenWebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy-loading für Provider (werden beim ersten Request initialisiert)
_ollama_provider: Optional[OllamaProvider] = None
_retrieval_strategy = None


def get_ollama():
    """Lazy-load Ollama Provider."""
    global _ollama_provider
    if _ollama_provider is None:
        _ollama_provider = OllamaProvider()
    return _ollama_provider


def get_retrieval():
    """Lazy-load Retrieval Strategy."""
    global _retrieval_strategy
    if _retrieval_strategy is None:
        _retrieval_strategy = get_retrieval_strategy()
    return _retrieval_strategy


# ============================================================================
# OpenAI-kompatible Pydantic Models
# ============================================================================

class Message(BaseModel):
    """Chat message."""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """OpenAI-kompatible Chat Completion Request."""
    model: str = "local-rag"
    messages: List[Message]
    stream: bool = False
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    # RAG-spezifische Optionen
    use_rag: bool = Field(default=True, description="RAG-Suche aktivieren")
    top_k: Optional[int] = Field(default=None, description="Anzahl Suchergebnisse")


class Choice(BaseModel):
    """Chat completion choice."""
    index: int
    message: Message
    finish_reason: str = "stop"


class StreamChoice(BaseModel):
    """Streaming choice delta."""
    index: int
    delta: dict
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    """Token usage stats."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI-kompatible Chat Completion Response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage = Usage()


class ModelInfo(BaseModel):
    """Model information."""
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "local"


class ModelsResponse(BaseModel):
    """Models list response."""
    object: str = "list"
    data: List[ModelInfo]


# RAG System Prompt
RAG_SYSTEM_PROMPT = """Du bist ein hilfreicher Assistent, der Fragen basierend auf dem bereitgestellten Kontext beantwortet.
Nutze die Kontextinformationen, um Fragen präzise zu beantworten. Wenn der Kontext nicht genügend 
Informationen enthält, sage das ehrlich. Zitiere Quellen wenn möglich.
Antworte immer auf Deutsch, es sei denn, der Nutzer fragt explizit auf einer anderen Sprache."""


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
async def root():
    """API Root - zeigt Basisinformationen."""
    return {
        "name": "Local Qdrant RAG API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "openai_compatible": True,
    }


@app.get("/health")
async def health():
    """Health-Check Endpoint."""
    health_status = {
        "status": "ok",
        "rag_enabled": True,
        "ollama": "unknown",
        "qdrant": "unknown",
    }
    
    # Prüfe Qdrant
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        health_status["qdrant"] = "ok"
        health_status["collections"] = len(collections.collections)
    except Exception as e:
        health_status["qdrant"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Prüfe Ollama
    try:
        provider = get_ollama()
        # Einfacher Test-Call
        test = provider.generate("test", stream=False)
        health_status["ollama"] = "ok"
    except Exception as e:
        health_status["ollama"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


@app.get("/v1/models", response_model=ModelsResponse)
async def list_models():
    """OpenAI-kompatible Model-Liste."""
    return ModelsResponse(
        data=[
            ModelInfo(id="local-rag", owned_by="local-qdrant-rag"),
            ModelInfo(id=settings.ollama.model, owned_by="ollama"),
        ]
    )


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI-kompatibler Chat-Endpoint mit RAG.
    
    Führt automatisch eine RAG-Suche durch und reichert den Kontext an,
    bevor die Anfrage an Ollama weitergeleitet wird.
    """
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    # Extrahiere die letzte User-Nachricht
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")
    
    query = user_messages[-1].content
    logger.info(f"[{request_id}] Query: {query[:100]}...")
    
    # RAG-Suche durchführen (falls aktiviert)
    context = ""
    sources = []
    
    if request.use_rag:
        try:
            retrieval = get_retrieval()
            top_k = request.top_k or settings.retrieval.top_k
            search_results = retrieval.search(query, top_k=top_k)
            
            if search_results:
                context_parts = []
                for i, result in enumerate(search_results, 1):
                    source_info = result.source or result.doc_id or f"Dokument {i}"
                    context_parts.append(f"[{i}] {source_info}\n{result.content}")
                    sources.append(source_info)
                
                context = "\n\n".join(context_parts)
                logger.info(f"[{request_id}] RAG: {len(search_results)} Ergebnisse gefunden")
            else:
                logger.info(f"[{request_id}] RAG: Keine relevanten Dokumente gefunden")
        except Exception as e:
            logger.warning(f"[{request_id}] RAG-Fehler: {e}")
            # Weiter ohne RAG-Kontext
    
    # Prompt mit Kontext erstellen
    if context:
        augmented_prompt = f"""Kontext aus der Wissensdatenbank:

{context}

---

Frage: {query}

Antworte basierend auf dem obigen Kontext:"""
    else:
        augmented_prompt = query
    
    # Chat-History für Ollama aufbauen (ohne die letzte User-Nachricht)
    history = [{"role": m.role, "content": m.content} for m in request.messages[:-1]]
    
    ollama = get_ollama()
    
    if request.stream:
        # Streaming Response
        async def generate_stream():
            try:
                for token in ollama.generate_stream(
                    prompt=augmented_prompt,
                    system_prompt=RAG_SYSTEM_PROMPT if request.use_rag else None,
                    context=history,
                ):
                    chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": token},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Final chunk
                final_chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }]
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"[{request_id}] Streaming error: {e}")
                error_chunk = {
                    "error": {"message": str(e), "type": "server_error"}
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    
    else:
        # Normale Response
        try:
            response_text = ollama.generate(
                prompt=augmented_prompt,
                system_prompt=RAG_SYSTEM_PROMPT if request.use_rag else None,
                context=history,
                stream=False,
            )
            
            # Füge Quellen-Info hinzu wenn gewünscht
            if sources and request.use_rag:
                response_text += f"\n\n📚 Quellen: {', '.join(sources[:3])}"
            
            return ChatCompletionResponse(
                id=request_id,
                created=created,
                model=request.model,
                choices=[
                    Choice(
                        index=0,
                        message=Message(role="assistant", content=response_text),
                    )
                ]
            )
            
        except Exception as e:
            logger.error(f"[{request_id}] Generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RAG-spezifische Endpoints
# ============================================================================

class SearchRequest(BaseModel):
    """RAG Search Request."""
    query: str
    top_k: int = 10
    strategy: Optional[str] = None


class SearchResult(BaseModel):
    """Single search result."""
    content: str
    source: Optional[str] = None
    score: float
    chunk_id: Optional[str] = None


class SearchResponse(BaseModel):
    """RAG Search Response."""
    results: List[SearchResult]
    query: str
    strategy: str
    total: int


@app.post("/v1/rag/search", response_model=SearchResponse)
async def rag_search(request: SearchRequest):
    """
    Direkte RAG-Suche ohne LLM-Generierung.
    
    Nützlich zum Testen der Retrieval-Qualität.
    """
    strategy_name = request.strategy or settings.retrieval.strategy
    retrieval = get_retrieval_strategy(strategy_name)
    
    results = retrieval.search(request.query, top_k=request.top_k)
    
    return SearchResponse(
        results=[
            SearchResult(
                content=r.content,
                source=r.source,
                score=r.score,
                chunk_id=r.chunk_id,
            )
            for r in results
        ],
        query=request.query,
        strategy=strategy_name,
        total=len(results),
    )


@app.get("/v1/rag/collections")
async def list_rag_collections():
    """Liste alle Qdrant Collections."""
    try:
        client = get_qdrant_client()
        collections = client.get_collections()
        
        result = []
        for coll in collections.collections:
            info = client.get_collection(coll.name)
            result.append({
                "name": coll.name,
                "points_count": info.points_count,
                "status": str(info.status),
            })
        
        return {
            "collections": result,
            "current": settings.qdrant.collection_name,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Server Entry Point
# ============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Start the API server."""
    import uvicorn
    logger.info(f"Starting Local Qdrant RAG API on {host}:{port}")
    logger.info(f"OpenWebUI: Add http://{host}:{port}/v1 as OpenAI API endpoint")
    uvicorn.run("src.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()

