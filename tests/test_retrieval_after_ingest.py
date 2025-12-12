"""Integration test for ingestion and retrieval pipeline."""

import logging
import tempfile
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test queries covering different retrieval scenarios
SMOKE_QUERIES = [
    "kurzer exakter Begriff aus einem Dokument",  # Tests Full-Text
    "semantisch ähnliche Umschreibung",  # Tests Embedding
    "Kombination aus beiden",  # Tests RRF-Merge
]


def create_test_document(content: str, filename: str, directory: str) -> str:
    """Create a test markdown document."""
    file_path = os.path.join(directory, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return file_path


def test_ingest_and_retrieval():
    """Test ingestion followed by retrieval with different query types."""
    from src.ingestion import ingest_directory
    from src.retrieval import get_retrieval_strategy
    
    # Create temporary directory with test documents
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test documents
        doc1_content = """
# Test Document 1

Dies ist ein Test-Dokument mit einem kurzen exakten Begriff aus einem Dokument.
Es enthält auch semantische Informationen über Machine Learning und künstliche Intelligenz.
"""
        doc2_content = """
# Test Document 2

Ein weiteres Dokument mit Informationen über Datenverarbeitung und Algorithmen.
Hier steht auch etwas über neuronale Netze und Deep Learning.
"""
        
        create_test_document(doc1_content, "test1.md", temp_dir)
        create_test_document(doc2_content, "test2.md", temp_dir)
        
        logger.info(f"Created test documents in {temp_dir}")
        
        # Ingest documents
        logger.info("Starting ingestion...")
        result = ingest_directory(temp_dir, recursive=False)
        logger.info(f"Ingestion result: {result}")
        
        assert result["processed"] > 0, "No documents were processed"
        assert result["failed"] == 0, f"Some documents failed: {result['failed']}"
        
        # Test retrieval strategies
        strategies = ["pure_semantic", "pure_fulltext", "hybrid_rrf"]
        
        for strategy_name in strategies:
            logger.info(f"\nTesting retrieval strategy: {strategy_name}")
            strategy = get_retrieval_strategy(strategy_name)
            
            for query in SMOKE_QUERIES:
                logger.info(f"  Query: '{query}'")
                results = strategy.search(query, top_k=5)
                
                assert len(results) > 0, f"No results returned for query: {query}"
                
                # Check that results have plausible scores
                for result in results:
                    assert result.content, "Result has no content"
                    assert result.score >= 0, f"Invalid score: {result.score}"
                    logger.info(f"    - Score: {result.score:.4f}, Source: {result.source}")
        
        logger.info("\n✅ All retrieval tests passed!")


if __name__ == "__main__":
    test_ingest_and_retrieval()

