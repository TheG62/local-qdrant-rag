#!/usr/bin/env python3
"""Comprehensive system health check for RAG Agent."""

import sys
import json
from pathlib import Path
from datetime import datetime

# Debug logging setup
LOG_PATH = Path("/Users/guneyyilmaz/local-qdrant-rag/.cursor/debug.log")

def debug_log(location, message, data=None, hypothesis_id=None, run_id="health-check"):
    """Write debug log entry."""
    log_entry = {
        "sessionId": "health-check",
        "runId": run_id,
        "hypothesisId": hypothesis_id or "general",
        "location": location,
        "message": message,
        "data": data or {},
        "timestamp": int(datetime.now().timestamp() * 1000),
    }
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Warning: Could not write log: {e}")

sys.path.insert(0, str(Path(__file__).parent))

def check_python_environment():
    """Check Python version and environment."""
    print("\n" + "="*60)
    print("1. PYTHON ENVIRONMENT")
    print("="*60)
    
    debug_log("system_health_check.py:check_python_environment", "Starting Python environment check")
    
    try:
        import sys
        python_version = sys.version_info
        python_path = sys.executable
        
        debug_log("system_health_check.py:check_python_environment", "Python info", {
            "version": f"{python_version.major}.{python_version.minor}.{python_version.micro}",
            "path": python_path
        })
        
        print(f"✅ Python Version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        print(f"✅ Python Path: {python_path}")
        
        # Check if venv is active
        if 'venv' in python_path or 'virtualenv' in python_path:
            print(f"✅ Virtual Environment: Active ({python_path})")
        else:
            print(f"⚠️ Virtual Environment: Not detected (using system Python)")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_python_environment", "Check failed", {"error": str(e)})
        print(f"❌ Error: {e}")
        return False


def check_dependencies():
    """Check all required dependencies."""
    print("\n" + "="*60)
    print("2. DEPENDENCIES")
    print("="*60)
    
    debug_log("system_health_check.py:check_dependencies", "Starting dependencies check")
    
    dependencies = {
        "docling": "Docling (IBM) for document processing",
        "torch": "PyTorch for ML operations",
        "sentence_transformers": "Sentence transformers for embeddings",
        "qdrant_client": "Qdrant client library",
        "click": "CLI framework",
        "ollama": "Ollama client",
    }
    
    all_ok = True
    
    for module_name, description in dependencies.items():
        try:
            module = __import__(module_name)
            version = getattr(module, "__version__", "unknown")
            debug_log("system_health_check.py:check_dependencies", "Module check", {
                "module": module_name,
                "version": version,
                "status": "ok"
            })
            print(f"✅ {module_name}: {version} - {description}")
        except ImportError:
            debug_log("system_health_check.py:check_dependencies", "Module missing", {
                "module": module_name,
                "status": "missing"
            })
            print(f"❌ {module_name}: NOT INSTALLED - {description}")
            all_ok = False
    
    return all_ok


def check_qdrant():
    """Check Qdrant connection and status."""
    print("\n" + "="*60)
    print("3. QDRANT VECTOR DATABASE")
    print("="*60)
    
    debug_log("system_health_check.py:check_qdrant", "Starting Qdrant check")
    
    try:
        from src.vectorstore import get_qdrant_client
        from src.settings import settings
        
        client = get_qdrant_client()
        debug_log("system_health_check.py:check_qdrant", "Qdrant client created", {"url": settings.qdrant.url})
        
        # Check connection
        collections = client.get_collections()
        debug_log("system_health_check.py:check_qdrant", "Qdrant connection", {
            "status": "ok",
            "collections_count": len(collections.collections)
        })
        
        print(f"✅ Qdrant URL: {settings.qdrant.url}")
        print(f"✅ Connection: OK")
        print(f"✅ Collections found: {len(collections.collections)}")
        
        # Check active collection
        collection_name = settings.qdrant.collection_name
        try:
            info = client.get_collection(collection_name)
            debug_log("system_health_check.py:check_qdrant", "Collection info", {
                "name": collection_name,
                "points": info.points_count,
                "status": str(info.status)
            })
            print(f"✅ Active Collection: {collection_name}")
            print(f"   - Points (Chunks): {info.points_count:,}")
            print(f"   - Status: {info.status}")
            print(f"   - Vector Dimension: {info.config.params.vectors.size}")
        except Exception as e:
            debug_log("system_health_check.py:check_qdrant", "Collection check failed", {"error": str(e)})
            print(f"⚠️ Collection '{collection_name}': {e}")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_qdrant", "Qdrant check failed", {"error": str(e)})
        print(f"❌ Qdrant Connection Failed: {e}")
        return False


def check_ollama():
    """Check Ollama connection and model."""
    print("\n" + "="*60)
    print("4. OLLAMA LLM")
    print("="*60)
    
    debug_log("system_health_check.py:check_ollama", "Starting Ollama check")
    
    try:
        from src.providers import OllamaProvider
        from src.settings import settings
        
        provider = OllamaProvider()
        debug_log("system_health_check.py:check_ollama", "Ollama provider created", {"model": settings.ollama.model})
        
        # Try a simple test query
        test_response = provider.generate("test", stream=False)
        debug_log("system_health_check.py:check_ollama", "Ollama test query", {
            "status": "ok",
            "response_length": len(test_response) if test_response else 0
        })
        
        print(f"✅ Ollama Model: {settings.ollama.model}")
        print(f"✅ Connection: OK")
        print(f"✅ Test Query: Successful")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_ollama", "Ollama check failed", {"error": str(e)})
        print(f"⚠️ Ollama Check Failed: {e}")
        print(f"   Make sure Ollama is running: ollama serve")
        print(f"   Install model: ollama pull {settings.ollama.model}")
        return False


def check_embeddings():
    """Check embedding model."""
    print("\n" + "="*60)
    print("5. EMBEDDING MODEL")
    print("="*60)
    
    debug_log("system_health_check.py:check_embeddings", "Starting embeddings check")
    
    try:
        from src.ingestion.embedder import get_embedder
        from src.settings import settings
        
        embedder = get_embedder()
        dimension = embedder.get_dimension()
        # Get model from embedder or settings
        model_name = getattr(settings, 'embedding', None)
        if model_name and hasattr(model_name, 'model'):
            model_str = model_name.model
        else:
            model_str = "BAAI/bge-m3"  # Default
        debug_log("system_health_check.py:check_embeddings", "Embedder check", {
            "model": model_str,
            "dimension": dimension
        })
        
        print(f"✅ Model: {model_str}")
        print(f"✅ Dimension: {dimension}")
        
        # Test embedding
        test_text = "Test embedding"
        embedding = embedder.embed([test_text])
        debug_log("system_health_check.py:check_embeddings", "Embedding test", {
            "status": "ok",
            "embedding_length": len(embedding[0]) if embedding else 0
        })
        
        print(f"✅ Test Embedding: Successful ({len(embedding[0])} dimensions)")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_embeddings", "Embeddings check failed", {"error": str(e)})
        print(f"❌ Embedding Model Failed: {e}")
        return False


def check_configuration():
    """Check configuration files."""
    print("\n" + "="*60)
    print("6. CONFIGURATION")
    print("="*60)
    
    debug_log("system_health_check.py:check_configuration", "Starting configuration check")
    
    try:
        from src.settings import settings
        
        # Get configuration values safely
        ollama_url = getattr(settings.ollama, 'url', 'http://localhost:11434')
        embedding_model = getattr(settings, 'embedding', None)
        if embedding_model and hasattr(embedding_model, 'model'):
            embedding_model_str = embedding_model.model
        else:
            embedding_model_str = "BAAI/bge-m3"
        
        config_items = {
            "Qdrant URL": settings.qdrant.url,
            "Qdrant Collection": settings.qdrant.collection_name,
            "Ollama Model": settings.ollama.model,
            "Ollama URL": ollama_url,
            "Embedding Model": embedding_model_str,
            "Retrieval Strategy": settings.retrieval.strategy,
            "Top K": settings.retrieval.top_k,
        }
        
        debug_log("system_health_check.py:check_configuration", "Configuration values", config_items)
        
        for key, value in config_items.items():
            print(f"✅ {key}: {value}")
        
        # Check .env file
        env_file = Path(".env")
        if env_file.exists():
            print(f"✅ .env file: Found")
        else:
            print(f"⚠️ .env file: Not found (using defaults)")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_configuration", "Configuration check failed", {"error": str(e)})
        print(f"❌ Configuration Check Failed: {e}")
        return False


def check_filesystem_functions():
    """Check filesystem functions."""
    print("\n" + "="*60)
    print("7. FILESYSTEM FUNCTIONS")
    print("="*60)
    
    debug_log("system_health_check.py:check_filesystem_functions", "Starting filesystem check")
    
    try:
        from src.filesystem import (
            get_current_dir,
            list_directory,
            navigate_to,
        )
        
        current = get_current_dir()
        debug_log("system_health_check.py:check_filesystem_functions", "Filesystem check", {
            "current_dir": str(current),
            "status": "ok"
        })
        
        print(f"✅ Navigation: OK")
        print(f"✅ Current Directory: {current}")
        
        # Test list_directory
        try:
            listing = list_directory(current)
            print(f"✅ List Directory: OK ({len(listing['files'])} files, {len(listing['directories'])} dirs)")
        except Exception as e:
            print(f"⚠️ List Directory: {e}")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_filesystem_functions", "Filesystem check failed", {"error": str(e)})
        print(f"❌ Filesystem Functions Failed: {e}")
        return False


def check_indexing_status():
    """Check indexing status."""
    print("\n" + "="*60)
    print("8. INDEXING STATUS")
    print("="*60)
    
    debug_log("system_health_check.py:check_indexing_status", "Starting indexing status check")
    
    try:
        from src.vectorstore import get_qdrant_client
        from src.settings import settings
        
        client = get_qdrant_client()
        info = client.get_collection(settings.qdrant.collection_name)
        
        debug_log("system_health_check.py:check_indexing_status", "Indexing status", {
            "points": info.points_count,
            "status": str(info.status)
        })
        
        print(f"✅ Indexed Chunks: {info.points_count:,}")
        print(f"✅ Collection Status: {info.status}")
        
        if info.points_count > 0:
            print(f"✅ Indexing: Active (data available)")
        else:
            print(f"⚠️ Indexing: No data yet (run: python -m src.cli ingest --directory /path)")
        
        return True
    except Exception as e:
        debug_log("system_health_check.py:check_indexing_status", "Indexing status check failed", {"error": str(e)})
        print(f"❌ Indexing Status Check Failed: {e}")
        return False


def main():
    """Run all health checks."""
    print("\n" + "="*60)
    print("SYSTEM HEALTH CHECK")
    print("="*60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    debug_log("system_health_check.py:main", "Starting comprehensive health check")
    
    results = []
    
    results.append(("Python Environment", check_python_environment()))
    results.append(("Dependencies", check_dependencies()))
    results.append(("Qdrant", check_qdrant()))
    results.append(("Ollama", check_ollama()))
    results.append(("Embeddings", check_embeddings()))
    results.append(("Configuration", check_configuration()))
    results.append(("Filesystem Functions", check_filesystem_functions()))
    results.append(("Indexing Status", check_indexing_status()))
    
    # Summary
    print("\n" + "="*60)
    print("HEALTH CHECK SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 All systems operational!")
    else:
        print("\n⚠️ Some checks failed. Please review the output above.")
    
    debug_log("system_health_check.py:main", "Health check completed", {"passed": passed, "total": total})
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

