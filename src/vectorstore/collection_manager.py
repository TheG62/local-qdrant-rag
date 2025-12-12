"""Collection management functions for Qdrant."""

import logging
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import CollectionStatus

from .qdrant_client import get_qdrant_client
from .schema import create_collection_schema
from ..settings import settings

logger = logging.getLogger(__name__)


def create_collection(
    name: str,
    vector_size: Optional[int] = None,
    client: Optional[QdrantClient] = None,
) -> bool:
    """
    Erstellt eine neue Collection.
    
    Args:
        name: Name der Collection
        vector_size: Vector-Dimension (defaults to settings)
        client: Qdrant client (creates new if None)
        
    Returns:
        True wenn erfolgreich erstellt, False wenn bereits existiert
        
    Raises:
        ValueError: Wenn Collection-Name ungültig ist
        ConnectionError: Wenn Qdrant nicht erreichbar ist
    """
    if not name or not name.strip():
        raise ValueError("Collection-Name darf nicht leer sein")
    
    name = name.strip()
    
    if client is None:
        client = get_qdrant_client()
    
    if vector_size is None:
        vector_size = settings.get_embedding_dimension()
    
    # Prüfe ob Collection bereits existiert
    collections = client.get_collections().collections
    collection_exists = any(c.name == name for c in collections)
    
    if collection_exists:
        logger.warning(f"Collection '{name}' existiert bereits")
        return False
    
    try:
        create_collection_schema(client, name, vector_size)
        logger.info(f"Collection '{name}' erfolgreich erstellt")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Collection '{name}': {e}")
        raise


def list_collections(client: Optional[QdrantClient] = None) -> List[Dict[str, any]]:
    """
    Listet alle Collections auf.
    
    Args:
        client: Qdrant client (creates new if None)
        
    Returns:
        Liste von Dicts mit Collection-Informationen
    """
    if client is None:
        client = get_qdrant_client()
    
    try:
        collections = client.get_collections().collections
        result = []
        
        for collection in collections:
            try:
                info = client.get_collection(collection.name)
                result.append({
                    "name": collection.name,
                    "points_count": info.points_count,
                    "status": str(info.status),
                    "vectors_count": info.vectors_count if hasattr(info, 'vectors_count') else 0,
                })
            except Exception as e:
                logger.warning(f"Konnte Info für Collection '{collection.name}' nicht abrufen: {e}")
                result.append({
                    "name": collection.name,
                    "points_count": 0,
                    "status": "unknown",
                    "vectors_count": 0,
                })
        
        return result
    except Exception as e:
        logger.error(f"Fehler beim Auflisten der Collections: {e}")
        raise


def delete_collection(
    name: str,
    client: Optional[QdrantClient] = None,
    force: bool = False,
) -> bool:
    """
    Löscht eine Collection.
    
    Args:
        name: Name der Collection
        client: Qdrant client (creates new if None)
        force: Wenn True, keine Bestätigung erforderlich
        
    Returns:
        True wenn erfolgreich gelöscht
        
    Raises:
        ValueError: Wenn Collection-Name ungültig oder nicht gefunden
        ConnectionError: Wenn Qdrant nicht erreichbar ist
    """
    if not name or not name.strip():
        raise ValueError("Collection-Name darf nicht leer sein")
    
    name = name.strip()
    
    if client is None:
        client = get_qdrant_client()
    
    # Prüfe ob Collection existiert
    collections = client.get_collections().collections
    collection_exists = any(c.name == name for c in collections)
    
    if not collection_exists:
        raise ValueError(f"Collection '{name}' existiert nicht")
    
    # Schutz: Standard-Collection nicht löschen ohne force
    if name == settings.qdrant.collection_name and not force:
        raise ValueError(
            f"Standard-Collection '{name}' kann nicht gelöscht werden. "
            f"Verwenden Sie --force wenn Sie sicher sind."
        )
    
    try:
        client.delete_collection(name)
        logger.info(f"Collection '{name}' erfolgreich gelöscht")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Löschen der Collection '{name}': {e}")
        raise


def get_collection_info(
    name: Optional[str] = None,
    client: Optional[QdrantClient] = None,
) -> Dict[str, any]:
    """
    Gibt Informationen über eine Collection zurück.
    
    Args:
        name: Collection-Name (defaults to settings)
        client: Qdrant client (creates new if None)
        
    Returns:
        Dict mit Collection-Informationen
    """
    if client is None:
        client = get_qdrant_client()
    
    if name is None:
        name = settings.qdrant.collection_name
    
    try:
        collection = client.get_collection(name)
        return {
            "name": name,
            "points_count": collection.points_count,
            "status": str(collection.status),
            "vectors_count": collection.vectors_count if hasattr(collection, 'vectors_count') else 0,
            "config": {
                "vector_size": collection.config.params.vectors.size if hasattr(collection.config.params, 'vectors') else None,
                "distance": str(collection.config.params.vectors.distance) if hasattr(collection.config.params, 'vectors') else None,
            },
        }
    except Exception as e:
        logger.warning(f"Konnte Info für Collection '{name}' nicht abrufen: {e}")
        return {
            "name": name,
            "points_count": 0,
            "status": "unknown",
            "vectors_count": 0,
            "config": {},
        }


def switch_collection(name: str) -> bool:
    """
    Wechselt die aktive Collection (ändert Settings).
    
    Hinweis: Diese Funktion ändert nur die aktuelle Session.
    Für persistente Änderung: Umgebungsvariable QDRANT_COLLECTION_NAME setzen.
    
    Args:
        name: Name der Collection
        
    Returns:
        True wenn erfolgreich gewechselt
    """
    if not name or not name.strip():
        raise ValueError("Collection-Name darf nicht leer sein")
    
    name = name.strip()
    
    # Prüfe ob Collection existiert
    client = get_qdrant_client()
    collections = client.get_collections().collections
    collection_exists = any(c.name == name for c in collections)
    
    if not collection_exists:
        raise ValueError(f"Collection '{name}' existiert nicht")
    
    # Ändere Settings für aktuelle Session
    settings.qdrant.collection_name = name
    logger.info(f"Aktive Collection geändert zu '{name}'")
    return True

