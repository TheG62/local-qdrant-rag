"""Intelligent file organization based on document content using Docling and Hybrid Search."""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from ..ingestion import load_document
from ..ingestion.embedder import get_embedder
from ..retrieval import get_retrieval_strategy
from ..vectorstore import get_qdrant_client
from ..settings import settings

logger = logging.getLogger(__name__)


def analyze_document_themes(
    directory: str | Path,
    recursive: bool = True,
    min_similarity: float = 0.7,
) -> Dict[str, List[str]]:
    """
    Analysiert Dokumente in einem Verzeichnis und gruppiert sie nach Themen.
    
    Nutzt Docling für Dokumentverarbeitung und Hybrid-Suche für Ähnlichkeitsanalyse.
    
    Args:
        directory: Verzeichnis mit Dokumenten
        recursive: Rekursiv durchsuchen
        min_similarity: Minimale Ähnlichkeit für Gruppierung
        
    Returns:
        Dict mit Themen als Keys und Listen von Dateipfaden als Values
    """
    from ..ingestion.document_loader import DOCLING_EXTENSIONS
    
    directory_path = Path(directory).expanduser()
    
    if not directory_path.exists():
        raise FileNotFoundError(f"Verzeichnis existiert nicht: {directory_path}")
    
    # Sammle alle unterstützten Dokumente
    pattern = "**/*" if recursive else "*"
    documents = []
    
    for file_path in directory_path.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in DOCLING_EXTENSIONS:
            try:
                # Nutze Docling für Dokumentverarbeitung
                doc = load_document(str(file_path))
                if doc:
                    documents.append({
                        "path": str(file_path),
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {}),
                    })
            except Exception as e:
                logger.warning(f"Konnte Dokument nicht laden {file_path}: {e}")
    
    if len(documents) < 2:
        logger.info("Zu wenige Dokumente für Themen-Analyse")
        return {}
    
    logger.info(f"Analysiere {len(documents)} Dokumente für Themen-Gruppierung...")
    
    # Nutze Embeddings für Ähnlichkeitsanalyse
    embedder = get_embedder()
    texts = [doc["content"][:5000] for doc in documents]  # Limit für Performance
    embeddings = embedder.embed(texts)
    
    # Gruppiere ähnliche Dokumente
    themes = defaultdict(list)
    used_indices = set()
    
    for i, doc in enumerate(documents):
        if i in used_indices:
            continue
        
        # Finde ähnliche Dokumente
        similar_docs = []
        current_embedding = embeddings[i]
        
        for j, other_doc in enumerate(documents):
            if i == j or j in used_indices:
                continue
            
            # Berechne Cosinus-Ähnlichkeit
            similarity = _cosine_similarity(current_embedding, embeddings[j])
            
            if similarity >= min_similarity:
                similar_docs.append((j, other_doc, similarity))
        
        if similar_docs:
            # Erstelle Themen-Name aus häufigsten Wörtern
            theme_name = _extract_theme_name(doc["content"])
            themes[theme_name].append(doc["path"])
            used_indices.add(i)
            
            for j, similar_doc, _ in similar_docs:
                themes[theme_name].append(similar_doc["path"])
                used_indices.add(j)
        else:
            # Einzelnes Dokument ohne ähnliche
            theme_name = _extract_theme_name(doc["content"])
            themes[theme_name].append(doc["path"])
            used_indices.add(i)
    
    logger.info(f"Gefundene Themen: {len(themes)}")
    return dict(themes)


def organize_by_themes(
    source_directory: str | Path,
    target_directory: str | Path,
    recursive: bool = True,
    min_similarity: float = 0.7,
    dry_run: bool = False,
) -> Dict[str, any]:
    """
    Organisiert Dokumente nach Themen in Ordnerstruktur.
    
    Nutzt Docling + Hybrid-Suche für intelligente Gruppierung.
    
    Args:
        source_directory: Quell-Verzeichnis
        target_directory: Ziel-Verzeichnis für organisierte Struktur
        recursive: Rekursiv durchsuchen
        min_similarity: Minimale Ähnlichkeit für Gruppierung
        dry_run: Nur simulieren, keine Dateien verschieben
        
    Returns:
        Dict mit Organisations-Ergebnissen
    """
    import shutil
    
    source_path = Path(source_directory).expanduser()
    target_path = Path(target_directory).expanduser()
    
    if not source_path.exists():
        raise FileNotFoundError(f"Quell-Verzeichnis existiert nicht: {source_path}")
    
    # Analysiere Themen
    themes = analyze_document_themes(source_path, recursive, min_similarity)
    
    if not themes:
        return {
            "themes_found": 0,
            "files_organized": 0,
            "dry_run": dry_run,
        }
    
    # Erstelle Ziel-Struktur
    if not dry_run:
        target_path.mkdir(parents=True, exist_ok=True)
    
    organized_count = 0
    theme_folders = {}
    
    for theme_name, file_paths in themes.items():
        # Bereinige Theme-Name für Ordner-Namen
        safe_theme_name = _sanitize_folder_name(theme_name)
        theme_folder = target_path / safe_theme_name
        
        if not dry_run:
            theme_folder.mkdir(parents=True, exist_ok=True)
        
        theme_folders[safe_theme_name] = []
        
        for file_path in file_paths:
            source_file = Path(file_path)
            if not source_file.exists():
                continue
            
            dest_file = theme_folder / source_file.name
            
            # Handle duplicate names
            counter = 1
            while dest_file.exists():
                stem = source_file.stem
                suffix = source_file.suffix
                dest_file = theme_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            if not dry_run:
                try:
                    shutil.move(str(source_file), str(dest_file))
                    organized_count += 1
                except Exception as e:
                    logger.error(f"Fehler beim Verschieben {source_file}: {e}")
            
            theme_folders[safe_theme_name].append(str(dest_file))
    
    return {
        "themes_found": len(themes),
        "files_organized": organized_count,
        "theme_folders": theme_folders,
        "dry_run": dry_run,
    }


def find_similar_documents(
    reference_file: str | Path,
    search_directory: Optional[str | Path] = None,
    top_k: int = 5,
    min_score: float = 0.6,
) -> List[Dict[str, any]]:
    """
    Finde ähnliche Dokumente zu einer Referenz-Datei.
    
    Nutzt Hybrid-Suche (semantisch + Volltext) für beste Ergebnisse.
    
    Args:
        reference_file: Referenz-Datei
        search_directory: Verzeichnis zum Durchsuchen (None = gesamte Collection)
        top_k: Anzahl ähnlicher Dokumente
        min_score: Minimaler Ähnlichkeits-Score
        
    Returns:
        Liste ähnlicher Dokumente mit Scores
    """
    from ..ingestion import load_document
    
    reference_path = Path(reference_file).expanduser()
    
    if not reference_path.exists():
        raise FileNotFoundError(f"Referenz-Datei existiert nicht: {reference_path}")
    
    # Lade Referenz-Dokument mit Docling
    ref_doc = load_document(str(reference_path))
    if not ref_doc:
        raise ValueError(f"Konnte Referenz-Dokument nicht laden: {reference_path}")
    
    # Nutze Hybrid-Suche für ähnliche Dokumente
    retrieval_strategy = get_retrieval_strategy("hybrid_rrf")
    
    # Suche nach ähnlichem Inhalt
    query = ref_doc["content"][:1000]  # Erste 1000 Zeichen als Query
    results = retrieval_strategy.search(query, top_k=top_k * 2)  # Mehr Ergebnisse für Filterung
    
    # Filtere nach Score und entferne die Referenz-Datei selbst
    similar_docs = []
    ref_source = str(reference_path)
    
    for result in results:
        if result.score >= min_score and result.source != ref_source:
            # Prüfe ob Datei im Such-Verzeichnis liegt (falls angegeben)
            if search_directory:
                search_path = Path(search_directory).expanduser()
                result_path = Path(result.source)
                try:
                    if not result_path.is_relative_to(search_path):
                        continue
                except ValueError:
                    continue
            
            similar_docs.append({
                "path": result.source,
                "score": result.score,
                "content_preview": result.content[:200],
            })
            
            if len(similar_docs) >= top_k:
                break
    
    return similar_docs


def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Berechne Cosinus-Ähnlichkeit zwischen zwei Vektoren."""
    import math
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(a * a for a in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)


def _extract_theme_name(content: str, max_words: int = 3) -> str:
    """Extrahiere Theme-Namen aus Dokument-Inhalt."""
    import re
    
    # Entferne Markdown/HTML Tags
    text = re.sub(r'<[^>]+>', '', content)
    text = re.sub(r'[#*`]', '', text)
    
    # Finde häufigste Wörter (außer Stopwords)
    words = re.findall(r'\b[a-zäöü]{4,}\b', text.lower())
    
    # Einfache Stopword-Liste (deutsch)
    stopwords = {
        'dass', 'dass', 'dies', 'diese', 'dieser', 'dieses', 'diesen',
        'eine', 'einer', 'einem', 'einen', 'eines', 'eins',
        'der', 'die', 'das', 'den', 'dem', 'des',
        'und', 'oder', 'aber', 'auch', 'sich', 'sind', 'ist',
        'werden', 'wird', 'wurde', 'wurden',
        'haben', 'hat', 'hatte', 'hatten',
        'sein', 'seine', 'seiner', 'seinem', 'seinen', 'seines',
        'kann', 'können', 'könnte', 'könnten',
        'soll', 'sollen', 'sollte', 'sollten',
        'wird', 'werden', 'wurde', 'wurden',
        'für', 'von', 'mit', 'über', 'unter', 'durch', 'bei',
    }
    
    words = [w for w in words if w not in stopwords]
    
    # Zähle Häufigkeit
    from collections import Counter
    word_counts = Counter(words)
    
    # Nimm häufigste Wörter
    theme_words = [word for word, _ in word_counts.most_common(max_words)]
    
    if theme_words:
        theme_name = "-".join(theme_words)
    else:
        theme_name = "diverses"
    
    return theme_name


def _sanitize_folder_name(name: str) -> str:
    """Bereinige Namen für Verzeichnis-Namen."""
    import re
    
    # Ersetze ungültige Zeichen
    name = re.sub(r'[<>:"/\\|?*]', '-', name)
    name = re.sub(r'\s+', '-', name)
    name = name.strip('-')
    
    # Limitiere Länge
    if len(name) > 50:
        name = name[:50]
    
    return name or "unnamed"

