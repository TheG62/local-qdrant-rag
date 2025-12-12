"""Intelligent organization using indexed knowledge (ERP-like suggestions)."""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict
import re

from ..ingestion import load_document
from ..ingestion.embedder import get_embedder
from ..retrieval import get_retrieval_strategy
from ..settings import settings

logger = logging.getLogger(__name__)


def suggest_organization_structure(
    directory: str | Path,
    use_indexed_knowledge: bool = True,
    recursive: bool = True,
) -> Dict[str, Any]:
    """
    Schlägt Organisations-Struktur basierend auf indexiertem Wissen vor.
    
    Ähnlich wie ein ERP-System:
    - Erkennt Kunden, Projekte, Verträge, Rechnungen aus indexiertem Wissen
    - Schlägt Ordnerstruktur vor (z.B. Kunden/Kunde_A/Verträge/)
    - Nutzt Hybrid-Suche um ähnliche Dokumente zu finden
    
    Args:
        directory: Verzeichnis zum Organisieren
        use_indexed_knowledge: Nutze indexiertes Wissen aus Qdrant
        recursive: Rekursiv durchsuchen
        
    Returns:
        Dict mit Vorschlägen für Organisations-Struktur
    """
    from ..ingestion.document_loader import DOCLING_EXTENSIONS
    
    directory_path = Path(directory).expanduser()
    
    if not directory_path.exists():
        raise FileNotFoundError(f"Verzeichnis existiert nicht: {directory_path}")
    
    # Sammle alle Dokumente
    pattern = "**/*" if recursive else "*"
    documents = []
    
    for file_path in directory_path.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in DOCLING_EXTENSIONS:
            try:
                doc = load_document(str(file_path))
                if doc:
                    documents.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "content": doc["content"],
                        "metadata": doc.get("metadata", {}),
                    })
            except Exception as e:
                logger.warning(f"Konnte Dokument nicht laden {file_path}: {e}")
    
    if not documents:
        return {
            "suggestions": [],
            "structure": {},
            "message": "Keine Dokumente gefunden",
        }
    
    logger.info(f"Analysiere {len(documents)} Dokumente für Organisations-Vorschläge...")
    
    suggestions = []
    structure = defaultdict(lambda: defaultdict(list))
    
    # Nutze indexiertes Wissen wenn verfügbar
    if use_indexed_knowledge:
        retrieval_strategy = get_retrieval_strategy("hybrid_rrf")
        
        # Kategorien die wir erkennen wollen
        categories = {
            "Kunden": ["kunde", "customer", "client", "auftraggeber"],
            "Projekte": ["projekt", "project", "auftrag"],
            "Verträge": ["vertrag", "contract", "vereinbarung", "agreement"],
            "Rechnungen": ["rechnung", "invoice", "bill", "zahlung"],
            "Angebote": ["angebot", "offer", "quote", "kostenvoranschlag"],
            "Mitarbeiter": ["mitarbeiter", "employee", "personal", "team"],
            "Marketing": ["marketing", "werbung", "kampagne", "campaign"],
        }
        
        for doc in documents:
            doc_content = doc["content"][:2000]  # Erste 2000 Zeichen für Analyse
            
            # Suche im indexierten Wissen nach ähnlichen Dokumenten
            try:
                search_results = retrieval_strategy.search(doc_content, top_k=5)
                
                # Analysiere Suchergebnisse um Kategorien zu finden
                found_categories = []
                for result in search_results:
                    result_content = result.content.lower()
                    result_source = result.source.lower()
                    
                    # Prüfe Kategorien
                    for category, keywords in categories.items():
                        if any(keyword in result_content or keyword in result_source for keyword in keywords):
                            if category not in found_categories:
                                found_categories.append(category)
                
                # Extrahiere Entitäten (Kunden, Projekte) aus Dokument
                entities = _extract_entities(doc_content)
                
                # Erstelle Vorschlag
                suggestion = {
                    "file": doc["name"],
                    "path": doc["path"],
                    "suggested_categories": found_categories or ["Diverses"],
                    "entities": entities,
                    "similar_docs": [
                        {
                            "source": r.source,
                            "score": r.score,
                        }
                        for r in search_results[:3]
                    ],
                }
                suggestions.append(suggestion)
                
                # Baue Struktur auf
                primary_category = found_categories[0] if found_categories else "Diverses"
                
                if entities.get("kunde"):
                    kunde = entities["kunde"]
                    structure[primary_category][kunde].append(doc["path"])
                elif entities.get("projekt"):
                    projekt = entities["projekt"]
                    structure[primary_category][projekt].append(doc["path"])
                else:
                    structure[primary_category]["Unkategorisiert"].append(doc["path"])
                    
            except Exception as e:
                logger.warning(f"Fehler bei Analyse von {doc['name']}: {e}")
                structure["Diverses"]["Unkategorisiert"].append(doc["path"])
    else:
        # Fallback: Einfache Themen-Analyse ohne indexiertes Wissen
        embedder = get_embedder()
        texts = [doc["content"][:5000] for doc in documents]
        embeddings = embedder.embed(texts)
        
        for i, doc in enumerate(documents):
            entities = _extract_entities(doc["content"])
            suggestion = {
                "file": doc["name"],
                "path": doc["path"],
                "suggested_categories": ["Diverses"],
                "entities": entities,
            }
            suggestions.append(suggestion)
            
            if entities.get("kunde"):
                structure["Kunden"][entities["kunde"]].append(doc["path"])
            else:
                structure["Diverses"]["Unkategorisiert"].append(doc["path"])
    
    # Formatiere Struktur für Ausgabe
    formatted_structure = {}
    for category, subcategories in structure.items():
        formatted_structure[category] = {
            subcat: len(files) for subcat, files in subcategories.items()
        }
    
    return {
        "suggestions": suggestions,
        "structure": formatted_structure,
        "total_documents": len(documents),
        "categories_found": len(formatted_structure),
    }


def organize_with_knowledge(
    source_directory: str | Path,
    target_base: str | Path,
    use_indexed_knowledge: bool = True,
    recursive: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Organisiert Dokumente basierend auf indexiertem Wissen (ERP-ähnlich).
    
    Erstellt Struktur wie:
    - Kunden/Kunde_A/Verträge/
    - Kunden/Kunde_A/Rechnungen/
    - Projekte/Projekt_X/
    
    Args:
        source_directory: Quell-Verzeichnis
        target_base: Basis-Verzeichnis für organisierte Struktur
        use_indexed_knowledge: Nutze indexiertes Wissen
        recursive: Rekursiv durchsuchen
        dry_run: Nur simulieren
        
    Returns:
        Dict mit Organisations-Ergebnissen
    """
    import shutil
    
    source_path = Path(source_directory).expanduser()
    target_path = Path(target_base).expanduser()
    
    if not source_path.exists():
        raise FileNotFoundError(f"Quell-Verzeichnis existiert nicht: {source_path}")
    
    # Hole Vorschläge
    suggestions_result = suggest_organization_structure(
        source_path,
        use_indexed_knowledge=use_indexed_knowledge,
        recursive=recursive,
    )
    
    if not suggestions_result.get("suggestions"):
        return {
            "organized": 0,
            "structure": {},
            "message": "Keine Dokumente zum Organisieren gefunden",
        }
    
    # Erstelle Ziel-Struktur
    if not dry_run:
        target_path.mkdir(parents=True, exist_ok=True)
    
    organized_count = 0
    created_folders = set()
    
    for suggestion in suggestions_result["suggestions"]:
        file_path = Path(suggestion["path"])
        if not file_path.exists():
            continue
        
        # Bestimme Ziel-Pfad basierend auf Vorschlag
        categories = suggestion.get("suggested_categories", ["Diverses"])
        primary_category = categories[0]
        
        entities = suggestion.get("entities", {})
        
        # Baue Pfad auf: Kategorie/Entität/Typ/
        target_folder_parts = [primary_category]
        
        if entities.get("kunde"):
            target_folder_parts.append(entities["kunde"])
            # Bestimme Dokument-Typ
            doc_type = _determine_document_type(suggestion["file"], suggestion.get("suggested_categories", []))
            if doc_type:
                target_folder_parts.append(doc_type)
        elif entities.get("projekt"):
            target_folder_parts.append(entities["projekt"])
        else:
            target_folder_parts.append("Unkategorisiert")
        
        target_folder = target_path / "/".join(target_folder_parts)
        
        if not dry_run:
            target_folder.mkdir(parents=True, exist_ok=True)
            created_folders.add(str(target_folder))
        
        dest_file = target_folder / file_path.name
        
        # Handle duplicates
        counter = 1
        while dest_file.exists():
            stem = file_path.stem
            suffix = file_path.suffix
            dest_file = target_folder / f"{stem}_{counter}{suffix}"
            counter += 1
        
        if not dry_run:
            try:
                shutil.move(str(file_path), str(dest_file))
                organized_count += 1
            except Exception as e:
                logger.error(f"Fehler beim Verschieben {file_path}: {e}")
    
    return {
        "organized": organized_count,
        "structure": suggestions_result["structure"],
        "folders_created": len(created_folders),
        "suggestions_used": len(suggestions_result["suggestions"]),
        "dry_run": dry_run,
    }


def _extract_entities(text: str) -> Dict[str, str]:
    """Extrahiere Entitäten (Kunden, Projekte) aus Text."""
    text_lower = text.lower()
    entities = {}
    
    # Suche nach Kunden-Namen (häufige Patterns)
    kunde_patterns = [
        r"kunde\s*:?\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
        r"customer\s*:?\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
        r"auftraggeber\s*:?\s*([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+)*)",
    ]
    
    for pattern in kunde_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities["kunde"] = match.group(1).strip()
            break
    
    # Suche nach Projekt-Namen
    projekt_patterns = [
        r"projekt\s*:?\s*([A-ZÄÖÜ][a-zäöüß0-9]+(?:\s+[A-ZÄÖÜ][a-zäöüß0-9]+)*)",
        r"project\s*:?\s*([A-ZÄÖÜ][a-zäöüß0-9]+(?:\s+[A-ZÄÖÜ][a-zäöüß0-9]+)*)",
    ]
    
    for pattern in projekt_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            entities["projekt"] = match.group(1).strip()
            break
    
    return entities


def _determine_document_type(filename: str, categories: List[str]) -> Optional[str]:
    """Bestimme Dokument-Typ basierend auf Dateiname und Kategorien."""
    filename_lower = filename.lower()
    
    if any("vertrag" in cat.lower() or "contract" in cat.lower() for cat in categories):
        return "Verträge"
    elif any("rechnung" in cat.lower() or "invoice" in cat.lower() for cat in categories):
        return "Rechnungen"
    elif any("angebot" in cat.lower() or "offer" in cat.lower() for cat in categories):
        return "Angebote"
    elif "vertrag" in filename_lower or "contract" in filename_lower:
        return "Verträge"
    elif "rechnung" in filename_lower or "invoice" in filename_lower:
        return "Rechnungen"
    elif "angebot" in filename_lower or "offer" in filename_lower:
        return "Angebote"
    
    return None

