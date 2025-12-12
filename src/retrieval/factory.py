"""Factory for retrieval strategies."""

import logging
from typing import Optional

from .base import RetrievalStrategy
from .semantic import PureSemanticRetrieval
from .fulltext import PureFullTextRetrieval
from .hybrid_rrf import HybridRRFRetrieval
from ..settings import settings

logger = logging.getLogger(__name__)


class RetrievalFactory:
    """Factory for creating retrieval strategy instances."""
    
    _strategies = {
        "pure_semantic": PureSemanticRetrieval,
        "pure_fulltext": PureFullTextRetrieval,
        "hybrid_rrf": HybridRRFRetrieval,
    }
    
    @classmethod
    def get_strategy(
        cls, 
        strategy_name: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> RetrievalStrategy:
        """
        Get a retrieval strategy instance.
        
        Args:
            strategy_name: Strategy name ('pure_semantic', 'pure_fulltext', 'hybrid_rrf')
                          Defaults to settings value
            min_score: Minimum score threshold (defaults to settings value)
        
        Returns:
            RetrievalStrategy instance
            
        Raises:
            ValueError: If strategy name is unknown
        """
        if strategy_name is None:
            strategy_name = settings.retrieval.strategy
        
        if min_score is None:
            min_score = settings.retrieval.min_score
        
        if strategy_name not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown retrieval strategy: {strategy_name}. "
                f"Available: {available}"
            )
        
        strategy_class = cls._strategies[strategy_name]
        logger.info(f"Using retrieval strategy: {strategy_name} (min_score={min_score})")
        return strategy_class(min_score=min_score)
    
    @classmethod
    def list_strategies(cls) -> list:
        """List available retrieval strategies."""
        return list(cls._strategies.keys())


# Convenience function
def get_retrieval_strategy(
    strategy_name: Optional[str] = None,
    min_score: Optional[float] = None,
) -> RetrievalStrategy:
    """
    Get a retrieval strategy instance (convenience function).
    
    Args:
        strategy_name: Strategy name (defaults to settings)
        min_score: Minimum score threshold (defaults to settings)
        
    Returns:
        RetrievalStrategy instance
    """
    return RetrievalFactory.get_strategy(strategy_name, min_score)
