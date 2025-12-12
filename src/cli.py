"""CLI interface for Local Qdrant RAG Agent."""

import logging
import re
import sys
import click
from pathlib import Path

from .settings import settings
from .ingestion import ingest_directory, ingest_file
from .retrieval import get_retrieval_strategy
from .tools import search_knowledge_base, format_search_results
from .providers import OllamaProvider
from .vectorstore.collection_manager import (
    create_collection,
    list_collections,
    delete_collection,
    get_collection_info as get_collection_info_manager,
    switch_collection,
)
from .filesystem import (
    get_current_dir,
    set_current_dir,
    list_directory,
    navigate_to,
    get_directory_tree,
    find_files,
    create_directory,
    create_file,
    move_file_or_directory,
    copy_file_or_directory,
    delete_file_or_directory,
    analyze_document_themes,
    organize_by_themes,
    find_similar_documents,
    suggest_organization_structure,
    organize_with_knowledge,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def _should_execute_now(query: str) -> bool:
    """Heuristik: nur bei klarer Bestätigung wirklich Dateien verschieben."""
    q = (query or "").lower()
    return any(k in q for k in ["jetzt", "wirklich", "ausführen", "ausfuehren", "mach das", "bitte jetzt"])


def _tidy_quick(source_dir: str | Path, target_dir: str | Path, dry_run: bool = True, max_files: int = 250) -> dict:
    """
    Schnelles, sicheres Aufräumen:
    - nur Top-Level Dateien (keine Unterordner anfassen)
    - nach Dateiendungen in grobe Kategorien verschieben
    """
    src = Path(source_dir).expanduser()
    dst = Path(target_dir).expanduser()
    if not src.exists() or not src.is_dir():
        raise ValueError(f"Quell-Verzeichnis existiert nicht: {src}")

    # Kategorien nach Extension (klein, bewusst grob)
    categories = {
        "Dokumente": {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".md", ".txt", ".rtf"},
        "Bilder": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tiff", ".bmp"},
        "Archive": {".zip", ".rar", ".7z", ".tar", ".gz"},
        "Code": {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".toml", ".ini", ".sh"},
        "AudioVideo": {".mp3", ".wav", ".m4a", ".mp4", ".mov", ".mkv"},
        "Sonstiges": set(),
    }

    files = [p for p in src.iterdir() if p.is_file() and not p.name.startswith(".")]
    too_many = len(files) > max_files

    plan = []
    moved = 0
    skipped = 0

    for p in files[:max_files]:
        ext = p.suffix.lower()
        cat = "Sonstiges"
        for name, exts in categories.items():
            if exts and ext in exts:
                cat = name
                break
        dest_folder = dst / cat
        dest_path = dest_folder / p.name
        plan.append({"from": str(p), "to": str(dest_path)})

    if dry_run:
        return {
            "mode": "dry_run",
            "source": str(src),
            "target": str(dst),
            "files_considered": len(files),
            "planned_moves": len(plan),
            "too_many": too_many,
            "note": "Nur Top-Level Dateien; Unterordner bleiben unangetastet.",
        }

    # Execute
    create_directory(dst)
    for item in plan:
        dest_folder = Path(item["to"]).parent
        create_directory(dest_folder)
        move_file_or_directory(item["from"], item["to"])
        moved += 1

    skipped = max(0, len(files) - moved)
    return {
        "mode": "executed",
        "source": str(src),
        "target": str(dst),
        "files_considered": len(files),
        "moved": moved,
        "skipped": skipped,
        "too_many": too_many,
        "note": "Nur Top-Level Dateien; Unterordner bleiben unangetastet.",
    }


# Patterns für Begrüßungen (kein RAG, kurze Antwort)
# WICHTIG: $ am Ende stellt sicher, dass es nur die Begrüßung ist, kein zusätzlicher Text
GREETING_PATTERNS = [
    r"^(hallo|hi|hey|moin|servus|grüß gott|guten (morgen|tag|abend))[\s!?.]*$",
    r"^(wie geht'?s|wie geht es dir|alles klar|was geht)[\s!?.]*$",
    r"^(danke|vielen dank|thx|thanks)(\s+(?:dir|danke|schön|für\s+(?:die\s+)?hilfe))?[\s!?.]*$",
    r"^(tschüss|bye|ciao|auf wiedersehen)[\s!?.]*$",
]

# Patterns für Meta-Fragen über den Assistenten (kein RAG, ausführliche Antwort)
# WICHTIG: Prüfe ob ein Pfad vorhanden ist - dann ist es KEINE Meta-Frage
META_PATTERNS = [
    r"^(was|wer) (bist|kannst) (du|ihr)[\s!?.]*$",
    r"^(was kannst du|wer bist du|was bist du)(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
    r"^(wie funktionierst du|wie arbeitest du)(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
    r"^(welche (dokumente|dateien|daten) (hast|kennst|stehen) (du|dir))(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
    r"^(was (weißt|weisst) du|was (hast|kannst) du (gelernt|gespeichert))(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
    r"^(hilfe|help|was kann ich (fragen|dich fragen))(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
    r"^(erkläre|erklär) (dich|mir wie du funktionierst)(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
    r"^(woher (hast|nimmst|bekommst) du (dein|die) (wissen|informationen|daten))(?!.*[/~])(?!.*\s+(?:in|von|zu|nach)\s+[/~]).*$",  # Kein Pfad
]

# Patterns für Indexierungs-Befehle
INDEX_PATTERNS = [
    # "indexiere /pfad/zum/ordner"
    r"^(indexiere|indiziere|lade|importiere|verarbeite|scanne|lies ein?)\s+(.+)$",
    # "füge /pfad/zum/ordner hinzu" - Pfad muss vor "hinzu" kommen
    r"^(füge|füg)\s+([^\s]+(?:\s+[^\s]+)*?)\s+(hinzu|zur datenbank|zur wissensdatenbank)$",
    # "lerne /pfad/zum/ordner"
    r"^(lerne|lern)\s+(.+)$",
    # "ingest /path/to/folder"
    r"^ingest\s+(.+)$",
]

# Patterns für Collection-Management-Befehle
COLLECTION_CREATE_PATTERNS = [
    r"^(erstelle|erstell|lege an|anlegen)\s+(?:eine\s+)?(?:neue\s+)?(?:wissensdatenbank|datenbank|collection)\s+(?:namens?|mit\s+dem\s+namen|genannt)\s+(.+)$",
    r"^(erstelle|erstell|lege an|anlegen)\s+(?:eine\s+)?(?:neue\s+)?(?:wissensdatenbank|datenbank|collection)\s+(.+)$",
    r"^(neue\s+)?(?:wissensdatenbank|datenbank|collection)\s+(.+)$",
]

COLLECTION_LIST_PATTERNS = [
    r"^(zeige|zeig|liste|list|zeige mir|zeig mir)\s+(?:alle\s+)?(?:wissensdatenbanken|datenbanken|collections)$",
    r"^(welche|was\s+sind\s+die)\s+(?:wissensdatenbanken|datenbanken|collections)(?:\s+gibt\s+es)?$",
    r"^(welche|was\s+sind\s+die)\s+(?:wissensdatenbanken|datenbanken|collections)\s+(?:gibt\s+es|existieren)$",
]

COLLECTION_DELETE_PATTERNS = [
    r"^(lösche|lösch|entferne|entfern|delete)\s+(?:die\s+)?(?:wissensdatenbank|datenbank|collection)\s+(.+)$",
    r"^(lösche|lösch|entferne|entfern|delete)\s+(.+)$",
]

COLLECTION_SWITCH_PATTERNS = [
    r"^(wechsel|wechsle|nutze|verwende|use|switch)\s+(?:zu|zur)\s+(?:der\s+)?(?:wissensdatenbank|datenbank|collection)\s+(.+)$",
    r"^(wechsel|wechsle|nutze|verwende|use|switch)\s+(?:zu|zur)\s+(.+)$",
    r"^(wechsel|wechsle|nutze|verwende|use|switch)\s+(.+)$",
]

COLLECTION_INFO_PATTERNS = [
    r"^(info|informationen|details|zeige info|zeige informationen)\s+(?:über|von|der|die)\s+(?:wissensdatenbank|datenbank|collection)\s+(.+)$",
    r"^(info|informationen|details)\s+(.+)$",
]

# Patterns für Dateisystem-Navigation
FS_LIST_PATTERNS = [
    r"^(zeige|zeig|liste|list|ls|zeige mir|zeig mir)\s+(?:den\s+)?(?:inhalt|inhalt von|dateien|dateien in)\s+(?:von|des|der|die)\s*(.+)$",
    r"^(was|welche|was für)\s+(?:befindet\s+sich|befidnet\s+sich|befidet\s+sich|befindt\s+sich|befinet\s+sich|ist|sind|gibt es)\s+(?:noch\s+)?(?:in\s+diesem\s+pfad|in\s+diesem\s+ordner|in|dort|darin|auf\s+meinem\s+desktop|auf\s+dem\s+desktop|hier)\s*:?\s*(.+)$",
    r"^(was|welche|was für)\s+(?:befindet\s+sich|befidnet\s+sich|befidet\s+sich|befindt\s+sich|befinet\s+sich|ist|sind|gibt es)\s+(?:noch\s+)?(?:auf\s+meinem\s+desktop|auf\s+dem\s+desktop)[\s!?.]*$",
    r"^(welche|was für)\s+(?:dateien|ordner|verzeichnisse|dokumente)\s+(?:gibt es|sind|befinden sich)\s+(?:in|dort|darin)\s*(.+)$",
    r"^(kannst\s+du\s+mir\s+)?(?:zusammenfassen|zeigen|zeig|liste|list|ls)\s+(?:was\s+)?(?:sich\s+)?(?:in\s+diesem\s+ordner|in\s+diesem\s+verzeichnis|in\s+diesem\s+pfad|auf\s+meinem\s+desktop|auf\s+dem\s+desktop)\s+(?:befindet|befidnet|befidet|befindt|befinet|ist|sind)\s*(.+)?$",
    r"^(zeige|zeig|liste|list|ls)\s+(.+)$",
    r"^(zeige|zeig|liste|list|ls)$",  # Aktuelles Verzeichnis
]

FS_NAVIGATE_PATTERNS = [
    r"^(navigiere|navigier|gehe|geh|cd|wechsel|wechsle)\s+(?:zu|nach|in|in das|in den|in die)\s+(.+)$",
    r"^(navigiere|navigier|gehe|geh|cd|wechsel|wechsle)\s+(.+)$",
]

FS_WHERE_PATTERNS = [
    r"^(wo\s+bin\s+ich|pwd|aktuelles\s+verzeichnis|aktueller\s+ordner)$",
]

FS_TREE_PATTERNS = [
    r"^(baum|tree|struktur|verzeichnisstruktur|zeige struktur)\s+(?:von|des|der|die)\s*(.+)$",
    r"^(baum|tree|struktur|verzeichnisstruktur|zeige struktur)\s+(.+)$",
    r"^(baum|tree|struktur|verzeichnisstruktur|zeige struktur)$",
]

# Patterns für Dateisystem-Operationen
FS_CREATE_DIR_PATTERNS = [
    r"^(erstelle|erstell|lege an|anlegen|mkdir)\s+(?:ein\s+)?(?:verzeichnis|ordner|ordner namens|verzeichnis namens)\s+(.+)$",
    r"^(erstelle|erstell|lege an|anlegen|mkdir)\s+(?!.*datei)(.+)$",  # Nicht wenn "datei" enthalten ist
]

FS_CREATE_FILE_PATTERNS = [
    r"^(erstelle|erstell|lege an|anlegen|touch)\s+(?:eine\s+)?(?:datei|datei namens)\s+(.+)$",
]

FS_MOVE_PATTERNS = [
    r"^(verschiebe|verschieb|move|mv|umbenennen|rename)\s+(.+)\s+(?:nach|zu|in)\s+(.+)$",
]

FS_COPY_PATTERNS = [
    r"^(kopiere|kopier|copy|cp)\s+(.+)\s+(?:nach|zu|in)\s+(.+)$",
]

FS_DELETE_PATTERNS = [
    r"^(lösche|lösch|delete|rm|entferne|entfern)\s+(?:die\s+)?(?:datei|ordner|verzeichnis)\s+(.+)$",
    r"^(lösche|lösch|delete|rm|entferne|entfern)\s+(.+)$",
]

# Patterns für intelligente Organisation
FS_ORGANIZE_PATTERNS = [
    r"^(organisiere|organisier|strukturiere|strukturier)\s+(?:die\s+)?(?:dokumente|dateien|desktop)\s+(?:in|von|des|der|die)\s*(.+)\s+(?:nach|nach themen|nach kategorien|mit wissen|intelligent)$",
    r"^(organisiere|organisier|strukturiere|strukturier)\s+(.+)\s+(?:nach|nach themen|nach kategorien|mit wissen|intelligent)$",
    # "räume (bitte) auf", "räume (bitte) auf den desktop", "räume (bitte) auf /pfad", "räum bitte auf"
    r"^(räume|räum)\s+(?:bitte\s+)?(?:auf(?:\s+den\s+desktop)?|den\s+desktop|das\s+verzeichnis)\s*(.+)?$",
]

FS_FIND_SIMILAR_PATTERNS = [
    r"^(finde|find|suche|such)\s+(?:ähnliche|ähnliche dateien|ähnliche dokumente)\s+(?:zu|von|für)\s+(.+)$",
    r"^(ähnliche|ähnliche dateien|ähnliche dokumente)\s+(?:zu|von|für)\s+(.+)$",
]


def extract_path_from_text(text: str) -> str | None:
    """
    Extrahiert einen Pfad aus einem Text, auch wenn Floskeln vorhanden sind.
    
    Sucht nach Pfaden die mit / oder ~ beginnen oder relative Pfade enthalten.
    Korrigiert häufige Tippfehler (z.B. "Destop" → "Desktop").
    
    Args:
        text: Text der möglicherweise einen Pfad enthält
        
    Returns:
        Extrahierter Pfad oder None
    """
    # Entferne Anführungszeichen am Anfang/Ende
    text = text.strip('"\'')
    
    # Korrigiere häufige Tippfehler in Pfaden VOR dem Pattern-Matching
    text_corrected = re.sub(r'\bDestop\b', 'Desktop', text, flags=re.IGNORECASE)
    text_corrected = re.sub(r'\bDokumente\b', 'Documents', text_corrected, flags=re.IGNORECASE)
    
    # Pattern 1: Absoluter Pfad (beginnt mit / oder ~) - ZUERST prüfen!
    # WICHTIG: Absolute Pfade haben Priorität, da sie spezifischer sind
    # Erlaubt auch Pfade mit Leerzeichen in Anführungszeichen
    # Wichtig: ~ muss von / gefolgt werden (nicht ~test sondern ~/test)
    
    # Zuerst: Home-Pfade (~/path) - MUSS mit ~/ beginnen!
    home_path_pattern = r'(~/(?:[^\s"]+(?:\s+[^\s"]+)*))'
    home_matches = re.findall(home_path_pattern, text_corrected)
    if home_matches:
        # Nimm den ersten Match
        path = home_matches[0].strip().strip('"\'')
        # Stoppe beim ersten "und" oder "dann" (um mehrere Pfade zu vermeiden)
        path = re.sub(r'\s+(?:und|dann).*$', '', path, flags=re.IGNORECASE)
        return path
    
    # Dann: Absolute Pfade (/path)
    # WICHTIG: Erkenne auch Pfade mit .. (Path Traversal) - wird später validiert
    # Pattern muss auch .. als Teil des Pfades erkennen
    # Suche nach / gefolgt von Pfad-Komponenten (kann auch .. enthalten)
    # Pattern: / gefolgt von beliebigen Zeichen (inkl. ..) bis zum ersten Leerzeichen oder Ende
    absolute_path_pattern = r'(/(?:[^\s"]+(?:/[^\s"]+)*))'
    matches = re.findall(absolute_path_pattern, text_corrected)
    if matches:
        # Nimm den ersten Match (nicht den längsten, um mehrere Pfade zu vermeiden)
        path = matches[0].strip().strip('"\'')
        # Stoppe beim ersten "und" oder "dann" (um mehrere Pfade zu vermeiden)
        path = re.sub(r'\s+(?:und|dann).*$', '', path, flags=re.IGNORECASE)
        # Stelle sicher, dass es mit / beginnt (nicht mit .)
        if path.startswith('/') and not path.startswith('./'):
            # Normalisiere doppelte Slashes, aber behalte führenden /
            normalized = re.sub(r'/+', '/', path)
            # Stelle sicher, dass es mit / beginnt
            if not normalized.startswith('/'):
                normalized = '/' + normalized
            return normalized
    
    # Pattern 2: Relativer Pfad (beginnt mit ./ oder ../) - NACH absoluten Pfaden prüfen!
    # Wichtig: Muss mit . beginnen, nicht nur / (sonst wird ./documents zu /documents)
    # WICHTIG: Nur wenn der Text wirklich mit . beginnt (nicht mitten im Text)
    # Prüfe ob Text mit ./ oder ../ beginnt
    if text.strip().startswith('./') or text.strip().startswith('../'):
        relative_path_pattern = r'^(\.\.?/[^\s"]+(?:\s+[^\s"]+)*)'
        match = re.match(relative_path_pattern, text.strip())
        if match:
            path = match.group(1).strip().strip('"\'')
            # Stelle sicher, dass es wirklich mit . beginnt
            if path.startswith('./') or path.startswith('../'):
                return path
    else:
        # Auch relative Pfade mitten im Text erkennen (aber nur wenn kein absoluter Pfad gefunden wurde)
        relative_path_pattern = r'(\.\.?/[^\s"]+(?:\s+[^\s"]+)*)'
        matches = re.findall(relative_path_pattern, text)
        if matches:
            # Nimm den längsten Match (wahrscheinlich der vollständige Pfad)
            path = max(matches, key=len).strip().strip('"\'')
            # Stelle sicher, dass es wirklich mit . beginnt
            if path.startswith('./') or path.startswith('../'):
                return path
    
    # Pattern 3: Pfad ohne führenden Slash (z.B. "documents/folder")
    # Nur wenn es wie ein Pfad aussieht (enthält /)
    # WICHTIG: Nur wenn es wirklich ein Pfad ist, nicht nur ein Wort mit /
    # WICHTIG: Nicht wenn es mit ~ beginnt (das haben wir schon abgefangen)
    if '/' in text and not text.strip().startswith('~') and not text.strip().startswith('/'):
        # Versuche den Teil nach dem letzten Befehlswort zu extrahieren
        # Entferne häufige Floskeln
        cleaned = re.sub(r'\b(bitte|den|gesamten|inhalt|von|aus)\s*:?\s*', '', text, flags=re.IGNORECASE)
        cleaned = cleaned.strip()
        # Prüfe ob es wirklich ein Pfad ist (mindestens 2 Teile mit /)
        if cleaned and '/' in cleaned and len(cleaned.split('/')) >= 2:
            # Stoppe beim ersten Leerzeichen nach dem Pfad (um mehrere Pfade zu vermeiden)
            # Aber erlaube Leerzeichen in Anführungszeichen
            path_match = re.search(r'([^\s"]+(?:/[^\s"]+)+)', cleaned)
            if path_match:
                path = path_match.group(1).strip('"\'')
                # Prüfe ob es wirklich ein Pfad ist (nicht nur ein Wort)
                if len(path.split('/')) >= 2:
                    return path
    
    return None


def is_greeting(query: str) -> bool:
    """Prüft ob die Query eine Begrüßung oder Small-Talk ist."""
    query_lower = query.lower().strip()
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, query_lower, re.IGNORECASE):
            return True
    return False


def is_meta_question(query: str) -> bool:
    """Prüft ob die Query eine Meta-Frage über den Assistenten ist."""
    query_lower = query.lower().strip()
    
    # Prüfe zuerst ob ein Pfad vorhanden ist - dann ist es KEINE Meta-Frage
    if extract_path_from_text(query):
        return False
    
    for pattern in META_PATTERNS:
        if re.match(pattern, query_lower, re.IGNORECASE):
            return True
    return False


def parse_index_command(query: str) -> dict | None:
    """
    Prüft ob die Query ein Indexierungs-Befehl ist.
    
    Returns:
        dict mit 'path' und 'recursive' oder None
    """
    # Normalisiere Query: Mehrere Leerzeichen zu einem, entferne Satzzeichen am Ende
    query_stripped = re.sub(r'\s+', ' ', query.strip())
    # Entferne Satzzeichen am Ende (?, !, .) für bessere Pattern-Erkennung
    query_stripped = re.sub(r'[!?.]+$', '', query_stripped).strip()
    
    # Wenn "und" oder "dann" im Text ist, nimm nur den ersten Teil
    # (um mehrere Befehle zu vermeiden)
    if ' und ' in query_stripped.lower() or ' dann ' in query_stripped.lower():
        parts = re.split(r'\s+(?:und|dann)\s+', query_stripped, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) > 1:
            query_stripped = parts[0].strip()
    
    # Prüfe ob es ein Indexierungs-Befehl ist
    is_index_command = False
    for pattern in INDEX_PATTERNS:
        if re.match(pattern, query_stripped, re.IGNORECASE):
            is_index_command = True
            break
    
    if not is_index_command:
        return None
    
    path_str = None
    
    # Für "füge X hinzu" Pattern: Extrahiere den Pfad vor "hinzu"
    if 'hinzu' in query_stripped.lower() or 'zur datenbank' in query_stripped.lower():
        # Finde die Position von "hinzu" oder "zur datenbank"
        hinzu_match = re.search(r'\s+(hinzu|zur datenbank|zur wissensdatenbank)', query_stripped, re.IGNORECASE)
        if hinzu_match:
            # Alles vor "hinzu" ist der Pfad
            before_hinzu = query_stripped[:hinzu_match.start()].strip()
            # Entferne den Befehlsteil ("füge" oder "füg")
            before_hinzu = re.sub(r'^(füge|füg)\s+', '', before_hinzu, flags=re.IGNORECASE)
            # Extrahiere den Pfad
            path_str = extract_path_from_text(before_hinzu)
    
    # Extrahiere den Pfad mit der robusten Funktion direkt aus der gesamten Query
    # Die Funktion kann Pfade auch erkennen wenn Floskeln davor stehen
    if not path_str:
        # WICHTIG: Prüfe zuerst ob relativer Pfad vorhanden ist (BEVOR extract_path_from_text)
        # Da extract_path_from_text absolute Pfade priorisiert, müssen wir relative Pfade separat prüfen
        relative_match = re.search(r'(\.\.?/[^\s"]+)', query_stripped)
        if relative_match:
            path_str = relative_match.group(1)
        
        if not path_str:
            path_str = extract_path_from_text(query_stripped)
        
        # Wenn mehrere Pfade gefunden werden könnten, nimm nur den ersten
        # (extract_path_from_text gibt bereits den ersten zurück, aber sicherstellen)
        if path_str and ' und ' in query_stripped.lower():
            # Wenn "und" im Text ist, könnte es mehrere Pfade geben
            # Nimm nur den Teil bis zum ersten "und"
            parts = query_stripped.split(' und ', 1)
            if len(parts) > 1:
                # Versuche Pfad aus dem ersten Teil zu extrahieren
                first_part_path = extract_path_from_text(parts[0])
                if first_part_path:
                    path_str = first_part_path
    
    # Fallback: Wenn kein Pfad gefunden wurde, versuche es mit dem Pattern-Matching
    if not path_str:
        for idx, pattern in enumerate(INDEX_PATTERNS):
            match = re.match(pattern, query_stripped, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Für "füge X hinzu" Pattern (Index 1): Gruppe 1 ist der Pfad, Gruppe 2 ist "hinzu"
                # Für andere Patterns: letzte Gruppe ist der Pfad
                if idx == 1 and len(groups) >= 2 and 'hinzu' in query_stripped.lower():
                    # Spezialbehandlung für "füge X hinzu" - nimm nur Gruppe 1 (der Pfad)
                    potential_path = groups[1].strip().strip('"\'')
                    # Entferne "hinzu" falls es noch drin ist
                    potential_path = re.sub(r'\s+hinzu.*$', '', potential_path, flags=re.IGNORECASE)
                elif groups:
                    potential_path = groups[-1].strip().strip('"\'')
                    # Für "füge X hinzu": Entferne "hinzu" am Ende falls vorhanden
                    if 'hinzu' in query_stripped.lower():
                        potential_path = re.sub(r'\s+hinzu.*$', '', potential_path, flags=re.IGNORECASE)
                else:
                    continue
                
                # Prüfe ob es wie ein Pfad aussieht
                # WICHTIG: ~ muss von / gefolgt werden (~/path), nicht nur ~ (z.B. ~test)
                is_valid_path = False
                if potential_path:
                    if potential_path.startswith('/') or potential_path.startswith('./') or potential_path.startswith('../'):
                        is_valid_path = True
                    elif potential_path.startswith('~/'):
                        is_valid_path = True
                    elif '/' in potential_path and not potential_path.startswith('~'):
                        is_valid_path = True
                
                if is_valid_path:
                    # Stoppe beim ersten "und" oder "dann" (um mehrere Befehle zu vermeiden)
                    potential_path = re.sub(r'\s+(?:und|dann).*$', '', potential_path, flags=re.IGNORECASE)
                    path_str = potential_path
                    break
    
    if not path_str:
        return None
    
    # Prüfe auf rekursiv-Flag (vor dem Entfernen von Floskeln)
    recursive = False
    if path_str.endswith(" -r") or path_str.endswith(" rekursiv"):
        recursive = True
        path_str = re.sub(r'\s+(-r|rekursiv)$', '', path_str)
    
    # Entferne häufige Floskeln am Anfang und Ende
    # Am Anfang: "bitte", "den gesamten inhalt", etc.
    path_str = re.sub(r'^(bitte\s+)?(den\s+gesamten\s+inhalt\s*:?\s*)?', '', path_str, flags=re.IGNORECASE)
    # Am Ende: "bitte", etc.
    path_str = re.sub(r'\s*(bitte|den|gesamten|inhalt|von|aus)\s*:?\s*$', '', path_str, flags=re.IGNORECASE)
    path_str = path_str.strip().strip('"\'')
    
    if not path_str:
        return None
    
    return {"path": path_str, "recursive": recursive}


def parse_collection_command(query: str) -> dict | None:
    """
    Prüft ob die Query ein Collection-Management-Befehl ist.
    
    Returns:
        dict mit 'action' und 'name' oder None
    """
    # Normalisiere Query: Mehrere Leerzeichen zu einem, entferne Satzzeichen am Ende
    query_stripped = re.sub(r'\s+', ' ', query.strip())
    # Entferne Satzzeichen am Ende (?, !, .) für bessere Pattern-Erkennung
    query_stripped = re.sub(r'[!?.]+$', '', query_stripped).strip()
    
    # Collection erstellen
    for pattern in COLLECTION_CREATE_PATTERNS:
        match = re.match(pattern, query_stripped, re.IGNORECASE)
        if match:
            name = match.groups()[-1].strip().strip('"\'')
            # Entferne Floskeln
            name = re.sub(r'\s*(namens?|mit\s+dem\s+namen|genannt)\s*', '', name, flags=re.IGNORECASE)
            # Stoppe beim ersten "und" oder "dann" (um mehrere Befehle zu vermeiden)
            name = re.sub(r'\s+(?:und|dann|oder).*$', '', name, flags=re.IGNORECASE)
            name = name.strip().strip('"\'')
            if name:
                return {"action": "create", "name": name}
    
    # Collections auflisten
    for pattern in COLLECTION_LIST_PATTERNS:
        if re.match(pattern, query_stripped, re.IGNORECASE):
            return {"action": "list"}
    
    # Collection löschen
    for pattern in COLLECTION_DELETE_PATTERNS:
        match = re.match(pattern, query_stripped, re.IGNORECASE)
        if match:
            name = match.groups()[-1].strip().strip('"\'')
            if name:
                return {"action": "delete", "name": name}
    
    # Collection wechseln
    for pattern in COLLECTION_SWITCH_PATTERNS:
        match = re.match(pattern, query_stripped, re.IGNORECASE)
        if match:
            name = match.groups()[-1].strip().strip('"\'')
            # Entferne Floskeln (wissensdatenbank, datenbank, collection)
            name = re.sub(r'\s*(?:der\s+)?(?:wissensdatenbank|datenbank|collection)\s+', '', name, flags=re.IGNORECASE)
            name = name.strip().strip('"\'')
            if name:
                return {"action": "switch", "name": name}
    
    # Collection Info
    for pattern in COLLECTION_INFO_PATTERNS:
        match = re.match(pattern, query_stripped, re.IGNORECASE)
        if match:
            name = match.groups()[-1].strip().strip('"\'')
            # Entferne Floskeln
            name = re.sub(r'\s*(über|von|der|die|wissensdatenbank|datenbank|collection)\s*', '', name, flags=re.IGNORECASE)
            name = name.strip().strip('"\'')
            if name:
                return {"action": "info", "name": name}
    
    return None


def parse_filesystem_command(query: str) -> dict | None:
    """
    Prüft ob die Query ein Dateisystem-Befehl ist.
    
    Returns:
        dict mit 'action' und Parametern oder None
    """
    # Normalisiere Query: Mehrere Leerzeichen zu einem, entferne Satzzeichen am Ende
    query_stripped = re.sub(r'\s+', ' ', query.strip())
    # Entferne Satzzeichen am Ende (?, !, .) für bessere Pattern-Erkennung
    query_stripped = re.sub(r'[!?.]+$', '', query_stripped).strip()

    # Für Parsing (Pattern-Matching) entfernen wir optionale "Bestätigungswörter" am Ende,
    # damit Sätze wie "... jetzt" trotzdem matchen – die Original-Query bleibt in cmd["query"] erhalten.
    parse_query = re.sub(
        r"\s+(?:jetzt|wirklich|ausführen|ausfuehren|mach\s+das)$",
        "",
        query_stripped,
        flags=re.IGNORECASE,
    ).strip()
    
    # WICHTIG: Prüfe zuerst ob es ein Collection-Befehl ist (höhere Priorität)
    # "zeige alle wissensdatenbanken" sollte Collection sein, nicht Filesystem
    # ABER: "zeige inhalt von /Users/test" sollte Filesystem sein, auch wenn "zeige" drin ist
    collection_result = parse_collection_command(parse_query)
    if collection_result:
        # Prüfe ob ein Pfad vorhanden ist - dann ist es Filesystem, nicht Collection
        has_path = extract_path_from_text(parse_query)
        if has_path:
            # Pfad vorhanden -> Filesystem hat Priorität
            pass  # Weiter mit Filesystem-Parsing
        else:
            # Kein Pfad -> Collection hat Priorität (z.B. "wechsel zu projekt-2025")
            if collection_result.get("action") in ["list", "create", "delete", "switch", "info"]:
                return None  # Collection-Befehl, nicht Filesystem
    
    # Navigation: Liste Verzeichnis
    for pattern in FS_LIST_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'') if match.groups() else None
            
            # Spezialbehandlung für "Desktop" - prüfe zuerst ob Desktop erwähnt wird
            if "desktop" in parse_query.lower():
                import os
                # Prüfe ob es ein expliziter Pfad ist (z.B. "/Users/.../Desktop")
                extracted_path = extract_path_from_text(parse_query)
                if extracted_path and "desktop" in extracted_path.lower():
                    path = extracted_path
                else:
                    # Wenn nur "Desktop" erwähnt wird ohne Pfad, verwende ~/Desktop
                    if not path or (path and not path.startswith("/") and not path.startswith("~") and "desktop" not in path.lower()):
                        path = os.path.expanduser("~/Desktop")
            
            # Extrahiere Pfad mit extract_path_from_text für bessere Erkennung und Korrektur
            # IMMER extract_path_from_text aufrufen für Tippfehler-Korrektur
            if path:
                extracted_path = extract_path_from_text(path)
                if extracted_path:
                    path = extracted_path
                else:
                    # Fallback: Versuche Pfad aus gesamter Query zu extrahieren
                    extracted_path = extract_path_from_text(parse_query)
                    if extracted_path:
                        path = extracted_path
            elif not path:
                # Wenn kein Pfad in Match, versuche aus gesamter Query zu extrahieren
                extracted_path = extract_path_from_text(parse_query)
                if extracted_path:
                    path = extracted_path
                elif "desktop" in parse_query.lower():
                    # Fallback: Wenn "Desktop" erwähnt wird, verwende ~/Desktop
                    import os
                    path = os.path.expanduser("~/Desktop")
            
            return {"action": "list", "path": path}
    
    # Navigation: Wechsel Verzeichnis
    for pattern in FS_NAVIGATE_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'')
            return {"action": "navigate", "path": path}
    
    # Navigation: Aktuelles Verzeichnis
    for pattern in FS_WHERE_PATTERNS:
        if re.match(pattern, parse_query, re.IGNORECASE):
            return {"action": "where"}
    
    # Navigation: Verzeichnisstruktur
    for pattern in FS_TREE_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'') if match.groups() else None
            return {"action": "tree", "path": path}
    
    # Operation: Ordner erstellen
    for pattern in FS_CREATE_DIR_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'')
            return {"action": "create_dir", "path": path}
    
    # Operation: Datei erstellen
    for pattern in FS_CREATE_FILE_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'')
            return {"action": "create_file", "path": path}
    
    # Operation: Verschieben
    for pattern in FS_MOVE_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            groups = match.groups()
            # groups: (verb, source, dest)
            if len(groups) >= 3:
                source = groups[1].strip().strip('"\'')
                dest = groups[2].strip().strip('"\'')
                return {"action": "move", "source": source, "dest": dest}
    
    # Operation: Kopieren
    for pattern in FS_COPY_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            groups = match.groups()
            # groups: (verb, source, dest)
            if len(groups) >= 3:
                source = groups[1].strip().strip('"\'')
                dest = groups[2].strip().strip('"\'')
                return {"action": "copy", "source": source, "dest": dest}
    
    # Operation: Löschen
    for pattern in FS_DELETE_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'')
            return {"action": "delete", "path": path}
    
    # Organisation: Nach Themen organisieren
    for pattern in FS_ORGANIZE_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            groups = match.groups()
            
            # Für "räume auf" Pattern
            if "räume" in parse_query.lower() or "räum" in parse_query.lower():
                # Pattern hat i.d.R. 2 Gruppen: (räume|räum) und optionaler Rest (z.B. /pfad)
                potential_source = None
                if groups and len(groups) >= 2 and groups[1]:
                    potential_source = groups[1].strip().strip('"\'')
                    # Falls nur Floskeln drin sind, ignorieren
                    if potential_source.lower() in ["", "bitte", "jetzt", "wirklich", "ausführen", "ausfuehren", "mach das"]:
                        potential_source = None

                if potential_source:
                    source = extract_path_from_text(potential_source) or potential_source
                elif "desktop" in parse_query.lower():
                    import os
                    source = os.path.expanduser("~/Desktop")
                else:
                    # Default zu Desktop
                    import os
                    source = os.path.expanduser("~/Desktop")
                dest = None
                return {"action": "organize", "source": source, "dest": dest, "query": query_stripped, "tidy": True}
            else:
                # Für normale "organisiere" Patterns - extrahiere Pfad mit extract_path_from_text
                # WICHTIG: Extrahiere Pfad AUS DER GESAMTEN QUERY, nicht aus cleaned_query
                # Da "nach themen" oder "mit wissen" am Ende steht, ist der Pfad davor
                
                # Versuche zuerst Pfad aus gesamter Query zu extrahieren
                source = extract_path_from_text(parse_query)
                
                if not source:
                    # Fallback: Entferne Befehlswörter und versuche nochmal
                    cleaned_query = re.sub(r'^(organisiere|organisier|strukturiere|strukturier)\s+(?:die\s+)?(?:dokumente|dateien|desktop)\s+(?:in|von|des|der|die)\s*', '', parse_query, flags=re.IGNORECASE)
                    cleaned_query = re.sub(r'^(organisiere|organisier|strukturiere|strukturier)\s+', '', cleaned_query, flags=re.IGNORECASE)
                    # Entferne "nach themen", "mit wissen" am Ende
                    cleaned_query = re.sub(r'\s+(?:nach|nach themen|nach kategorien|mit wissen|intelligent).*$', '', cleaned_query, flags=re.IGNORECASE)
                    source = extract_path_from_text(cleaned_query) or cleaned_query.strip()
                
                if not source:
                    # Fallback: verwende erste Gruppe
                    # groups: (verb, source, ...)
                    if groups and len(groups) >= 2 and groups[1]:
                        source = groups[1].strip().strip('"\'')
                    else:
                        continue
                
                # Entferne "nach themen", "mit wissen", etc. am Ende für dest
                dest_match = re.search(r'\s+(?:nach|in|zu)\s+(.+)$', parse_query, re.IGNORECASE)
                dest = dest_match.groups()[0].strip().strip('"\'') if dest_match else None
            
            return {"action": "organize", "source": source, "dest": dest, "query": query_stripped, "tidy": False}
    
    # Suche: Ähnliche Dokumente finden
    for pattern in FS_FIND_SIMILAR_PATTERNS:
        match = re.match(pattern, parse_query, re.IGNORECASE)
        if match:
            path = match.groups()[-1].strip().strip('"\'')
            return {"action": "find_similar", "path": path}
    
    return None


def execute_filesystem_command(cmd: dict) -> str:
    """
    Führt einen Dateisystem-Befehl aus.
    
    Args:
        cmd: Befehl-Dict mit 'action' und Parametern
        
    Returns:
        Statusmeldung als String
    """
    try:
        action = cmd.get("action")
        
        if action == "list":
            path = cmd.get("path")
            # Korrigiere Pfad falls Tippfehler vorhanden
            if path:
                corrected_path = extract_path_from_text(path)
                if corrected_path and corrected_path != path:
                    path = corrected_path
            result = list_directory(path)
            
            lines = [f"📁 Inhalt von {result['path']}:\n"]
            
            if result["directories"]:
                lines.append("📂 Verzeichnisse:")
                for dir_info in result["directories"]:
                    item_count = dir_info.get("item_count", "?")
                    lines.append(f"   📂 {dir_info['name']}/ ({item_count} Einträge)")
            
            if result["files"]:
                lines.append("\n📄 Dateien:")
                for file_info in result["files"]:
                    size = file_info.get("size", 0)
                    size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
                    lines.append(f"   📄 {file_info['name']} ({size_str})")
            
            if not result["directories"] and not result["files"]:
                lines.append("   (leer)")
            
            return "\n".join(lines)
        
        elif action == "navigate":
            path = cmd.get("path")
            if not path:
                return "❌ Pfad fehlt"
            new_dir = navigate_to(path)
            return f"✅ Navigiert zu: {new_dir}"
        
        elif action == "where":
            current = get_current_dir()
            return f"📂 Aktuelles Verzeichnis: {current}"
        
        elif action == "tree":
            path = cmd.get("path")
            tree_lines = get_directory_tree(path)
            if tree_lines:
                return "\n".join(tree_lines)
            else:
                return "⚠️ Keine Einträge gefunden"
        
        elif action == "create_dir":
            path = cmd.get("path")
            if not path:
                return "❌ Pfad fehlt"
            created = create_directory(path)
            return f"✅ Verzeichnis erstellt: {created}"
        
        elif action == "create_file":
            path = cmd.get("path")
            if not path:
                return "❌ Pfad fehlt"
            created = create_file(path)
            return f"✅ Datei erstellt: {created}"
        
        elif action == "move":
            source = cmd.get("source")
            dest = cmd.get("dest")
            if not source or not dest:
                return "❌ Quelle oder Ziel fehlt"
            moved = move_file_or_directory(source, dest)
            return f"✅ Verschoben: {source} -> {moved}"
        
        elif action == "copy":
            source = cmd.get("source")
            dest = cmd.get("dest")
            if not source or not dest:
                return "❌ Quelle oder Ziel fehlt"
            copied = copy_file_or_directory(source, dest)
            return f"✅ Kopiert: {source} -> {copied}"
        
        elif action == "delete":
            path = cmd.get("path")
            if not path:
                return "❌ Pfad fehlt"
            # Sicherheitsabfrage würde hier kommen
            deleted = delete_file_or_directory(path, force=False)
            return f"✅ Gelöscht: {path}"
        
        elif action == "organize":
            source = cmd.get("source")
            dest = cmd.get("dest")
            query = cmd.get("query", "")
            tidy = bool(cmd.get("tidy"))
            
            if not source:
                return "❌ Quell-Verzeichnis fehlt"
            
            # Prüfe ob "mit wissen" oder "intelligent" in Query steht
            query_lower = query.lower() if query else ""
            use_knowledge = "mit wissen" in query_lower or "intelligent" in query_lower or "wissen" in query_lower

            # Schneller "Aufräumen"-Modus: Default Dry-Run, nur Top-Level Dateien
            if tidy and not use_knowledge:
                source_path = Path(source).expanduser()
                if not dest:
                    dest = str(source_path.parent / f"{source_path.name}_aufgeraeumt")
                dry_run = not _should_execute_now(query)

                result = _tidy_quick(source, dest, dry_run=dry_run, max_files=250)
                if result["mode"] == "dry_run":
                    lines = [
                        "🧹 Aufräumen (Vorschau / Dry-Run):",
                        f"   📂 Quelle: {result['source']}",
                        f"   📂 Ziel:   {result['target']}",
                        f"   📄 Top-Level Dateien: {result['files_considered']}",
                        f"   🔁 Geplante Verschiebungen: {result['planned_moves']} (Limit: 250)",
                        f"   ℹ️  {result['note']}",
                        "   ✅ Zum Ausführen: schreibe z.B. 'räume bitte auf jetzt'",
                    ]
                    if result.get("too_many"):
                        lines.append("   ⚠️  Sehr viele Dateien – es werden maximal 250 pro Lauf verschoben.")
                    return "\n".join(lines)

                lines = [
                    "✅ Aufräumen abgeschlossen:",
                    f"   📂 Quelle: {result['source']}",
                    f"   📂 Ziel:   {result['target']}",
                    f"   📄 Verschoben: {result['moved']}",
                    f"   ⏭️  Übersprungen: {result['skipped']}",
                    f"   ℹ️  {result['note']}",
                ]
                if result.get("too_many"):
                    lines.append("⚠️  Hinweis: Es wurden nur 250 Dateien pro Lauf verschoben.")
                return "\n".join(lines)

            # Default für "organisiere ..." (egal ob mit Wissen oder nach Themen):
            # erst Vorschau (dry_run), wirklich ausführen nur bei expliziter Bestätigung ("jetzt"/"wirklich"/"ausführen")
            dry_run = not _should_execute_now(query)
            
            # Wenn kein Ziel angegeben, erstelle strukturiertes Verzeichnis
            if not dest:
                source_path = Path(source).expanduser()
                suffix = "_organisiert_wissen" if use_knowledge else "_organisiert"
                dest = str(source_path.parent / f"{source_path.name}{suffix}")
            
            if use_knowledge:
                from .filesystem.knowledge_organizer import organize_with_knowledge, suggest_organization_structure
                
                click.echo(f"🧠 Analysiere Dokumente mit indexiertem Wissen (ERP-ähnlich)...")
                
                # Zeige Vorschläge zuerst
                suggestions = suggest_organization_structure(source, use_indexed_knowledge=True)
                
                if suggestions.get("suggestions"):
                    click.echo(f"\n💡 Vorschläge für {len(suggestions['suggestions'])} Dokumente:")
                    for i, sug in enumerate(suggestions["suggestions"][:5], 1):
                        categories = ", ".join(sug.get("suggested_categories", ["Diverses"]))
                        entities = sug.get("entities", {})
                        entity_str = ""
                        if entities.get("kunde"):
                            entity_str = f" (Kunde: {entities['kunde']})"
                        elif entities.get("projekt"):
                            entity_str = f" (Projekt: {entities['projekt']})"
                        click.echo(f"   {i}. {sug['file']} → {categories}{entity_str}")
                    if len(suggestions["suggestions"]) > 5:
                        click.echo(f"   ... und {len(suggestions['suggestions']) - 5} weitere")
                
                result = organize_with_knowledge(source, dest, use_indexed_knowledge=True, dry_run=dry_run)
                
                lines = [
                    f"✅ Intelligente Organisation {'(Vorschau)' if dry_run else 'abgeschlossen'}:",
                    f"   📊 {result.get('suggestions_used', 0)} Dokumente analysiert",
                    f"   📁 {result['organized']} Dateien organisiert",
                    f"   📂 {result.get('folders_created', 0)} Ordner erstellt",
                    f"   📂 Ziel-Verzeichnis: {dest}",
                ]
                if dry_run:
                    lines.append("   ✅ Zum Ausführen: hänge 'jetzt' an (z.B. 'organisiere ... mit wissen jetzt')")
                
                if result.get("structure"):
                    lines.append("\n📂 Erstellte Struktur:")
                    for category, subcats in result["structure"].items():
                        lines.append(f"   📂 {category}/")
                        for subcat, count in subcats.items():
                            lines.append(f"      📁 {subcat}/ ({count} Dateien)")
            else:
                click.echo(f"🔄 Analysiere Dokumente mit Docling und Hybrid-Suche...")
                result = organize_by_themes(source, dest, dry_run=dry_run)
                
                lines = [
                    f"✅ Organisation {'(Vorschau)' if dry_run else 'abgeschlossen'}:",
                    f"   📊 {result['themes_found']} Themen gefunden",
                    f"   📁 {result['files_organized']} Dateien organisiert",
                    f"   📂 Ziel-Verzeichnis: {dest}",
                ]
                if dry_run:
                    lines.append("   ✅ Zum Ausführen: hänge 'jetzt' an (z.B. 'organisiere ... nach themen jetzt')")
                
                if result.get("theme_folders"):
                    lines.append("\n📂 Erstellte Ordner:")
                    for theme, files in result["theme_folders"].items():
                        lines.append(f"   📂 {theme}/ ({len(files)} Dateien)")
            
            return "\n".join(lines)
        
        elif action == "find_similar":
            path = cmd.get("path")
            if not path:
                return "❌ Datei-Pfad fehlt"
            
            click.echo(f"🔍 Suche ähnliche Dokumente mit Hybrid-Suche...")
            similar = find_similar_documents(path, top_k=5)
            
            if not similar:
                return f"⚠️ Keine ähnlichen Dokumente zu {path} gefunden"
            
            lines = [f"🔍 Ähnliche Dokumente zu {Path(path).name}:\n"]
            for i, doc in enumerate(similar, 1):
                lines.append(f"{i}. {doc['path']} (Score: {doc['score']:.3f})")
                lines.append(f"   {doc['content_preview'][:100]}...")
            
            return "\n".join(lines)
        
        else:
            return f"❌ Unbekannte Aktion: {action}"
    
    except Exception as e:
        logger.exception(f"Dateisystem-Befehl fehlgeschlagen: {e}")
        return f"❌ Fehler: {e}"


def execute_collection_command(action: str, name: str | None = None) -> str:
    """
    Führt einen Collection-Management-Befehl aus.
    
    Args:
        action: Aktion ('create', 'list', 'delete', 'switch', 'info')
        name: Collection-Name (bei create, delete, switch, info)
        
    Returns:
        Statusmeldung als String
    """
    try:
        if action == "create":
            if not name:
                return "❌ Collection-Name fehlt"
            success = create_collection(name)
            if success:
                return f"✅ Wissensdatenbank '{name}' wurde erstellt"
            else:
                return f"⚠️ Wissensdatenbank '{name}' existiert bereits"
        
        elif action == "list":
            collections = list_collections()
            if not collections:
                return "Keine Wissensdatenbanken gefunden."
            
            current = settings.qdrant.collection_name
            lines = ["📚 Verfügbare Wissensdatenbanken:\n"]
            
            for coll in collections:
                marker = "👉 " if coll["name"] == current else "   "
                status_icon = "✅" if coll["status"] == "green" else "⚠️"
                lines.append(
                    f"{marker}{status_icon} {coll['name']} "
                    f"({coll['points_count']} Chunks)"
                )
            
            return "\n".join(lines)
        
        elif action == "delete":
            if not name:
                return "❌ Collection-Name fehlt"
            try:
                delete_collection(name, force=False)
                return f"✅ Wissensdatenbank '{name}' wurde gelöscht"
            except ValueError as e:
                return f"❌ {e}"
        
        elif action == "switch":
            if not name:
                return "❌ Collection-Name fehlt"
            try:
                switch_collection(name)
                return f"✅ Verwende jetzt Wissensdatenbank '{name}'"
            except ValueError as e:
                return f"❌ {e}"
        
        elif action == "info":
            info = get_collection_info_manager(name)
            lines = [f"📊 Informationen zu '{info['name']}':\n"]
            lines.append(f"  Chunks: {info['points_count']}")
            lines.append(f"  Status: {info['status']}")
            if info.get('config', {}).get('vector_size'):
                lines.append(f"  Vector-Dimension: {info['config']['vector_size']}")
            return "\n".join(lines)
        
        else:
            return f"❌ Unbekannte Aktion: {action}"
    
    except Exception as e:
        logger.exception(f"Collection-Befehl fehlgeschlagen: {e}")
        return f"❌ Fehler: {e}"


def execute_indexing(path_str: str, recursive: bool = False) -> str:
    """
    Führt die Indexierung aus und gibt eine Statusmeldung zurück.
    
    Args:
        path_str: Pfad zum Dokument oder Verzeichnis
        recursive: Ob rekursiv indexiert werden soll (None = Auto-Detection)
        
    Returns:
        Statusmeldung als String
    """
    path = Path(path_str).expanduser()
    
    if not path.exists():
        return f"❌ Pfad nicht gefunden: {path}"
    
    try:
        if path.is_file():
            click.echo(f"📄 Indexiere Datei: {path}")
            result = ingest_file(str(path))
        elif path.is_dir():
            # Für Verzeichnisse: Standardmäßig rekursiv, es sei denn explizit deaktiviert
            # Das macht Sinn, da Dateien meist in Unterordnern liegen
            if recursive is False:
                # Prüfe ob im Root-Verzeichnis Dateien vorhanden sind
                root_files = list(path.glob("*"))
                root_files = [f for f in root_files if f.is_file() and f.suffix.lower() in {
                    '.pdf', '.docx', '.pptx', '.xlsx', '.html', '.htm', '.md', '.txt',
                    '.png', '.jpg', '.jpeg', '.tiff', '.bmp'
                }]
                
                if not root_files:
                    # Keine Dateien im Root -> automatisch rekursiv
                    recursive = True
                    click.echo(f"ℹ️  Keine Dateien im Root-Verzeichnis gefunden, suche rekursiv...")
            
            mode = "rekursiv" if recursive else "nur oberste Ebene"
            click.echo(f"📁 Indexiere Verzeichnis ({mode}): {path}")
            result = ingest_directory(str(path), recursive=recursive)
        else:
            return f"❌ Unbekannter Pfadtyp: {path}"
        
        # Ergebnis formatieren
        processed = result.get("processed", 0)
        failed = result.get("failed", 0)
        failed_files = result.get("failed_files", 0)
        
        status_parts = [f"✅ Indexierung abgeschlossen: {processed} Chunks verarbeitet"]
        
        if failed > 0:
            status_parts.append(f"⚠️ {failed} Chunks fehlgeschlagen")
        if failed_files > 0:
            status_parts.append(f"⚠️ {failed_files} Dateien konnten nicht verarbeitet werden")
        
        if processed == 0 and failed == 0:
            status_parts = ["⚠️ Keine unterstützten Dokumente gefunden."]
            status_parts.append("Unterstützte Formate: PDF, DOCX, PPTX, XLSX, HTML, MD, TXT, PNG, JPG")
        
        return "\n".join(status_parts)
        
    except Exception as e:
        logger.exception(f"Indexierung fehlgeschlagen: {e}")
        return f"❌ Indexierung fehlgeschlagen: {e}"


def check_qdrant_health():
    """Check if Qdrant is reachable."""
    try:
        from .vectorstore import get_qdrant_client
        client = get_qdrant_client()
        collections = client.get_collections()
        logger.info("✅ Qdrant is reachable")
        return True
    except Exception as e:
        logger.error(f"❌ Qdrant health check failed: {e}")
        return False


def check_ollama_health():
    """Check if Ollama is reachable."""
    try:
        provider = OllamaProvider()
        # Try a simple test query
        test_response = provider.generate("test", stream=False)
        logger.info("✅ Ollama is reachable")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Ollama health check failed: {e}")
        logger.info("Make sure Ollama is running and the model is installed:")
        logger.info(f"  ollama pull {settings.ollama.model}")
        return False


def get_collection_info() -> dict:
    """Get information about the current collection."""
    try:
        from .vectorstore import get_qdrant_client
        client = get_qdrant_client()
        collection = client.get_collection(settings.qdrant.collection_name)
        return {
            "name": settings.qdrant.collection_name,
            "points_count": collection.points_count,
            "status": str(collection.status),
        }
    except Exception:
        return {"name": settings.qdrant.collection_name, "points_count": 0, "status": "unknown"}


@click.group()
def cli():
    """Local Qdrant RAG Agent - CLI for local RAG operations."""
    pass


@cli.command()
@click.option(
    "-d", "--directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    help="Directory containing documents to ingest",
)
@click.option(
    "-f", "--file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Single file to ingest",
)
@click.option(
    "-r", "--recursive",
    is_flag=True,
    help="Recursively process directories",
)
@click.option(
    "--batch-size",
    default=100,
    help="Batch size for processing",
)
def ingest(directory, file, recursive, batch_size):
    """Ingest documents into Qdrant."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        if directory:
            result = ingest_directory(directory, recursive=recursive, batch_size=batch_size)
        elif file:
            result = ingest_file(file, batch_size=batch_size)
        else:
            click.echo("Error: Either --directory or --file must be specified", err=True)
            sys.exit(1)
        
        click.echo(f"✅ Successfully ingested {result['processed']} chunks")
        if result.get("failed", 0) > 0:
            click.echo(f"⚠️ Failed to ingest {result['failed']} chunks", err=True)
        if result.get("failed_files", 0) > 0:
            click.echo(f"⚠️ Failed to process {result['failed_files']} files", err=True)
    except Exception as e:
        click.echo(f"❌ Ingestion failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option(
    "--strategy",
    type=click.Choice(["pure_semantic", "pure_fulltext", "hybrid_rrf"]),
    default=None,
    help="Retrieval strategy (defaults to settings)",
)
@click.option(
    "--top-k",
    default=None,
    type=int,
    help="Number of results to return",
)
@click.option(
    "--show-sources",
    is_flag=True,
    help="Show source information",
)
def search(query, strategy, top_k, show_sources):
    """Search the knowledge base."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        results = search_knowledge_base(query, strategy=strategy, top_k=top_k)
        
        if not results:
            click.echo("No results found.")
            return
        
        click.echo(f"\nFound {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            click.echo(f"[{i}] Score: {result.score:.4f}")
            if show_sources and result.source:
                click.echo(f"    Source: {result.source}")
            click.echo(f"    {result.content[:200]}...")
            click.echo()
    except Exception as e:
        click.echo(f"❌ Search failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--strategy",
    type=click.Choice(["pure_semantic", "pure_fulltext", "hybrid_rrf"]),
    default=None,
    help="Retrieval strategy (defaults to settings)",
)
@click.option(
    "--show-sources",
    is_flag=True,
    help="Show source documents after each response",
)
@click.option(
    "--no-stream",
    is_flag=True,
    help="Disable streaming (wait for complete response)",
)
def chat(strategy, show_sources, no_stream):
    """Start an interactive chat session."""
    if not check_qdrant_health():
        sys.exit(1)
    
    if not check_ollama_health():
        click.echo("Warning: Ollama may not be available. Chat may fail.", err=True)
    
    click.echo("🤖 Local Qdrant RAG Chat Session")
    click.echo("=" * 50)
    click.echo("Stelle deine Fragen oder:")
    click.echo("  - 'exit' oder 'quit' zum Beenden")
    click.echo("  - 'clear' um den Verlauf zu löschen")
    click.echo("  - 'indexiere /pfad/zum/ordner' um Dokumente hinzuzufügen")
    click.echo("  - 'indexiere /pfad -r' für rekursive Indexierung")
    click.echo("  - 'erstelle wissensdatenbank projekt-2025' - Neue Wissensdatenbank")
    click.echo("  - 'zeige alle wissensdatenbanken' - Liste anzeigen")
    click.echo("  - 'wechsel zu projekt-2025' - Wissensdatenbank wechseln")
    click.echo("  - 'ls' oder 'zeige inhalt von /pfad' - Verzeichnis anzeigen")
    click.echo("  - 'cd /pfad' oder 'navigiere zu /pfad' - Verzeichnis wechseln")
    click.echo("  - 'organisiere /pfad nach themen' - Dokumente organisieren")
    click.echo("  - 'organisiere /pfad mit wissen' - ERP-ähnlich mit indexiertem Wissen")
    click.echo("  - 'räume auf den desktop' - Desktop aufräumen")
    click.echo("  - 'finde ähnliche dokumente zu /pfad' - Ähnliche Dokumente finden")
    click.echo("=" * 50)
    click.echo()
    
    retrieval_strategy = get_retrieval_strategy(strategy)
    ollama_provider = OllamaProvider()
    chat_history = []
    
    # System-Prompt für RAG-basierte Antworten
    system_prompt = """Du bist ein hilfreicher Assistent, der Fragen basierend auf dem bereitgestellten Kontext beantwortet.
Nutze die Kontextinformationen, um Fragen präzise zu beantworten. Wenn der Kontext nicht genügend 
Informationen enthält, sage das ehrlich. Zitiere Quellen wenn möglich.
Antworte immer auf Deutsch, es sei denn, der Nutzer fragt explizit auf einer anderen Sprache."""

    # System-Prompt für Begrüßungen
    greeting_system_prompt = """Du bist ein freundlicher Assistent. Antworte kurz und natürlich auf Deutsch."""
    
    # System-Prompt für Meta-Fragen über den Assistenten
    meta_system_prompt = """Du bist ein lokaler RAG-Assistent (Retrieval Augmented Generation) für deutsche Unternehmen.

Deine Fähigkeiten:
- Du durchsuchst eine lokale Wissensdatenbank mit Dokumenten
- Du beantwortest Fragen basierend auf den gefundenen Dokumenten
- Du zitierst Quellen wenn möglich
- Du antwortest auf Deutsch
- Du kannst neue Dokumente indexieren wenn der Nutzer einen Pfad angibt

Befehle die der Nutzer nutzen kann:
- "indexiere /pfad/zum/ordner" - Dokumente indexieren
- "indexiere /pfad -r" - Rekursiv indexieren (inkl. Unterordner)
- "erstelle wissensdatenbank NAME" - Neue Wissensdatenbank erstellen
- "zeige alle wissensdatenbanken" - Liste aller Wissensdatenbanken
- "wechsel zu NAME" - Zu anderer Wissensdatenbank wechseln
- "lösche wissensdatenbank NAME" - Wissensdatenbank löschen

Technische Details:
- Dokumentverarbeitung: Docling (IBM) - PDF, Word, Excel, PowerPoint, HTML, Markdown, Images (OCR)
- Embedding-Modell: BGE-M3 (multilingual, 1024 Dimensionen)
- Vector-Datenbank: Qdrant (lokal)
- LLM: Ollama (lokal, qwen2.5)
- Suche: Hybrid (semantisch + Volltext mit RRF-Merge)

Du bist GDPR-konform - alle Daten bleiben lokal, nichts wird in die Cloud gesendet.

Antworte freundlich und informativ auf Meta-Fragen über dich selbst."""
    
    use_streaming = not no_stream
    
    while True:
        try:
            query = input("\nDu: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ["exit", "quit"]:
                click.echo("\nChat wird beendet...")
                break
            
            if query.lower() == "clear":
                chat_history = []
                click.echo("Verlauf gelöscht.")
                continue
            
            # Prüfen ob es ein Dateisystem-Befehl ist
            fs_cmd = parse_filesystem_command(query)
            if fs_cmd:
                click.echo()
                result_msg = execute_filesystem_command(fs_cmd)
                click.echo(f"\nAssistent: {result_msg}")
                continue
            
            # Prüfen ob es ein Collection-Management-Befehl ist
            collection_cmd = parse_collection_command(query)
            if collection_cmd:
                click.echo()
                result_msg = execute_collection_command(
                    collection_cmd["action"],
                    collection_cmd.get("name")
                )
                click.echo(f"\nAssistent: {result_msg}")
                
                # Bei Switch: Collection-Info aktualisieren
                if collection_cmd["action"] == "switch":
                    collection_info = get_collection_info()
                    click.echo(f"📊 Wissensdatenbank: {collection_info['points_count']} Chunks")
                continue
            
            # Prüfen ob es ein Indexierungs-Befehl ist
            index_cmd = parse_index_command(query)
            if index_cmd:
                click.echo()
                result_msg = execute_indexing(index_cmd["path"], index_cmd["recursive"])
                click.echo(f"\nAssistent: {result_msg}")
                
                # Collection-Info aktualisieren und anzeigen
                collection_info = get_collection_info()
                click.echo(f"📊 Wissensdatenbank: {collection_info['points_count']} Chunks")
                continue
            
            # Prüfen ob es eine Begrüßung ist
            if is_greeting(query):
                click.echo("\nAssistent: ", nl=False)
                
                if use_streaming:
                    response_parts = []
                    for token in ollama_provider.generate_stream(
                        prompt=query,
                        system_prompt=greeting_system_prompt,
                        context=chat_history,
                    ):
                        click.echo(token, nl=False)
                        response_parts.append(token)
                        sys.stdout.flush()
                    response = "".join(response_parts)
                    click.echo()
                else:
                    response = ollama_provider.generate(
                        prompt=query,
                        system_prompt=greeting_system_prompt,
                        context=chat_history,
                        stream=False,
                    )
                    click.echo(response)
                
                chat_history.append({"role": "user", "content": query})
                chat_history.append({"role": "assistant", "content": response})
                continue
            
            # Prüfen ob es eine Meta-Frage ist
            if is_meta_question(query):
                # Collection-Info für Meta-Antworten holen
                collection_info = get_collection_info()
                
                meta_context = f"""Aktuelle Wissensdatenbank:
- Collection: {collection_info['name']}
- Anzahl Dokumente/Chunks: {collection_info['points_count']}
- Status: {collection_info['status']}"""
                
                prompt_with_context = f"""{meta_context}

Frage des Nutzers: {query}

Beantworte die Frage über dich selbst:"""
                
                click.echo("\nAssistent: ", nl=False)
                
                if use_streaming:
                    response_parts = []
                    for token in ollama_provider.generate_stream(
                        prompt=prompt_with_context,
                        system_prompt=meta_system_prompt,
                        context=chat_history,
                    ):
                        click.echo(token, nl=False)
                        response_parts.append(token)
                        sys.stdout.flush()
                    response = "".join(response_parts)
                    click.echo()
                else:
                    response = ollama_provider.generate(
                        prompt=prompt_with_context,
                        system_prompt=meta_system_prompt,
                        context=chat_history,
                        stream=False,
                    )
                    click.echo(response)
                
                chat_history.append({"role": "user", "content": query})
                chat_history.append({"role": "assistant", "content": response})
                continue
            
            # RAG-Suche für echte Fragen
            search_results = retrieval_strategy.search(query, top_k=settings.retrieval.top_k)
            
            # Kontext aus Suchergebnissen aufbauen
            context_parts = []
            for i, result in enumerate(search_results, 1):
                source_info = result.source or result.doc_id or f"Dokument {i}"
                context_parts.append(f"[{i}] {source_info}\n{result.content}")
            
            context = "\n\n".join(context_parts) if context_parts else "Keine relevanten Dokumente gefunden."
            
            # Prompt mit Kontext erstellen
            prompt = f"""Kontext aus der Wissensdatenbank:

{context}

Frage: {query}

Antworte basierend auf dem obigen Kontext:"""
            
            # Antwort generieren
            click.echo("\nAssistent: ", nl=False)
            
            if use_streaming:
                response_parts = []
                for token in ollama_provider.generate_stream(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=chat_history,
                ):
                    click.echo(token, nl=False)
                    response_parts.append(token)
                    sys.stdout.flush()
                response = "".join(response_parts)
                click.echo()
            else:
                response = ollama_provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=chat_history,
                    stream=False,
                )
                click.echo(response)
            
            # Zum Verlauf hinzufügen
            chat_history.append({"role": "user", "content": query})
            chat_history.append({"role": "assistant", "content": response})
            
            # Quellen anzeigen wenn gewünscht
            if show_sources and search_results:
                click.echo("\n📚 Quellen:")
                for i, result in enumerate(search_results, 1):
                    source_info = result.source or result.doc_id or f"Dokument {i}"
                    click.echo(f"  {i}. {source_info} (Score: {result.score:.4f})")
            
        except KeyboardInterrupt:
            click.echo("\n\nChat wird beendet...")
            break
        except Exception as e:
            click.echo(f"\n❌ Fehler: {e}", err=True)
            logger.exception("Chat error")


@cli.group()
def collection():
    """Manage Qdrant collections (Wissensdatenbanken)."""
    pass


@collection.command("create")
@click.argument("name")
@click.option(
    "--vector-size",
    default=None,
    type=int,
    help="Vector dimension (defaults to embedding model dimension)",
)
def collection_create(name, vector_size):
    """Create a new collection."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        success = create_collection(name, vector_size=vector_size)
        if success:
            click.echo(f"✅ Collection '{name}' erfolgreich erstellt")
        else:
            click.echo(f"⚠️ Collection '{name}' existiert bereits", err=True)
            sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Fehler beim Erstellen der Collection: {e}", err=True)
        sys.exit(1)


@collection.command("list")
def collection_list():
    """List all collections."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        collections = list_collections()
        
        if not collections:
            click.echo("Keine Collections gefunden.")
            return
        
        click.echo("\n📚 Verfügbare Wissensdatenbanken:\n")
        
        # Aktuelle Collection markieren
        current_collection = settings.qdrant.collection_name
        
        for coll in collections:
            marker = "👉 " if coll["name"] == current_collection else "   "
            status_icon = "✅" if coll["status"] == "green" else "⚠️"
            click.echo(
                f"{marker}{status_icon} {coll['name']} "
                f"({coll['points_count']} Chunks, Status: {coll['status']})"
            )
        
        click.echo()
    except Exception as e:
        click.echo(f"❌ Fehler beim Auflisten der Collections: {e}", err=True)
        sys.exit(1)


@collection.command("delete")
@click.argument("name")
@click.option(
    "--force",
    is_flag=True,
    help="Force deletion without confirmation",
)
def collection_delete(name, force):
    """Delete a collection."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        # Bestätigung wenn nicht force
        if not force:
            click.echo(f"⚠️ Möchten Sie die Collection '{name}' wirklich löschen?")
            click.echo("Diese Aktion kann nicht rückgängig gemacht werden!")
            confirmation = input("Geben Sie 'JA' ein um fortzufahren: ")
            if confirmation != "JA":
                click.echo("Abgebrochen.")
                return
        
        delete_collection(name, force=force)
        click.echo(f"✅ Collection '{name}' erfolgreich gelöscht")
    except ValueError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Fehler beim Löschen der Collection: {e}", err=True)
        sys.exit(1)


@collection.command("info")
@click.argument("name", required=False)
def collection_info(name):
    """Show information about a collection."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        info = get_collection_info_manager(name)
        
        click.echo(f"\n📊 Informationen zu Collection '{info['name']}':\n")
        click.echo(f"  Chunks: {info['points_count']}")
        click.echo(f"  Status: {info['status']}")
        if info.get('config', {}).get('vector_size'):
            click.echo(f"  Vector-Dimension: {info['config']['vector_size']}")
        if info.get('config', {}).get('distance'):
            click.echo(f"  Distance-Metrik: {info['config']['distance']}")
        click.echo()
    except Exception as e:
        click.echo(f"❌ Fehler: {e}", err=True)
        sys.exit(1)


@collection.command("use")
@click.argument("name")
def collection_use(name):
    """Switch to a different collection (for current session)."""
    if not check_qdrant_health():
        sys.exit(1)
    
    try:
        switch_collection(name)
        click.echo(f"✅ Verwende jetzt Collection '{name}'")
        click.echo("Hinweis: Diese Änderung gilt nur für die aktuelle Session.")
        click.echo(f"Für persistente Änderung: QDRANT_COLLECTION_NAME={name} setzen")
    except ValueError as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Fehler: {e}", err=True)
        sys.exit(1)


@cli.command()
def health():
    """Check health of Qdrant and Ollama services."""
    qdrant_ok = check_qdrant_health()
    ollama_ok = check_ollama_health()
    
    # Show collection info
    if qdrant_ok:
        collection_info = get_collection_info()
        click.echo(f"📊 Collection '{collection_info['name']}': {collection_info['points_count']} chunks")
    
    if qdrant_ok and ollama_ok:
        click.echo("✅ All services are healthy")
        sys.exit(0)
    else:
        click.echo("❌ Some services are not available", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="Host to bind the server to",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to run the server on",
)
@click.option(
    "--reload",
    is_flag=True,
    help="Enable auto-reload for development",
)
def serve(host, port, reload):
    """Start the OpenAI-compatible API server.
    
    Startet einen API-Server der mit OpenWebUI, Continue.dev und anderen
    OpenAI-kompatiblen Tools funktioniert.
    
    Beispiel:
        python -m src.cli serve --port 8000
    
    Dann in OpenWebUI:
        Settings → Connections → OpenAI API
        Base URL: http://localhost:8000/v1
    """
    click.echo("🚀 Starte Local Qdrant RAG API Server...")
    click.echo(f"   Host: {host}")
    click.echo(f"   Port: {port}")
    click.echo(f"   OpenAPI Docs: http://{host}:{port}/docs")
    click.echo(f"   OpenWebUI URL: http://{host}:{port}/v1")
    click.echo()
    
    try:
        from .api import run_server
        run_server(host=host, port=port, reload=reload)
    except ImportError as e:
        click.echo(f"❌ API-Dependencies fehlen: {e}", err=True)
        click.echo("   Installiere mit: pip install fastapi uvicorn", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Server-Fehler: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
