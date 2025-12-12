"""
Docs Consistency Smoke Test

Prüft, dass die in README.md dokumentierten Chat-Befehle
tatsächlich vom Parser erkannt werden und die CLI-Commands existieren.

Verhindert Drift zwischen Dokumentation und Implementation.
"""

import subprocess
import sys
from pathlib import Path

import pytest

# Importiere Parser-Funktionen
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.cli import (
    parse_filesystem_command,
    parse_collection_command,
    parse_index_command,
    is_greeting,
    is_meta_question,
)


# ============================================================================
# README Chat-Beispiele die funktionieren MÜSSEN
# ============================================================================

# Format: (query, expected_route, description)
# Routes: "filesystem", "collection", "index", "greeting", "meta", "rag"

README_CHAT_EXAMPLES = [
    # Indexierungs-Befehle (README Zeile ~191-206)
    ("indexiere /pfad/zum/ordner", "index", "Einfacher Index-Befehl"),
    ("indexiere ./documents", "index", "Relativer Pfad"),
    ("füge /pfad hinzu", "index", "Füge hinzu Variante"),
    ("indexiere /pfad -r", "index", "Rekursiv Flag"),
    ("indexiere /pfad rekursiv", "index", "Rekursiv Wort"),
    
    # Collection-Management (README Zeile ~217-233)
    ("erstelle wissensdatenbank projekt-2025", "collection", "Collection erstellen"),
    ("zeige alle wissensdatenbanken", "collection", "Collections auflisten"),
    ("wechsel zu projekt-2025", "collection", "Collection wechseln (ohne Pfad)"),
    ("lösche wissensdatenbank alte-collection", "collection", "Collection löschen"),
    ("info projekt-2025", "collection", "Collection Info"),
    
    # Dateisystem-Navigation (README Zeile ~237-253)
    ("ls", "filesystem", "Liste aktuelles Verzeichnis"),
    ("zeige inhalt von /Users/test", "filesystem", "Zeige Inhalt"),
    ("cd /Users/test", "filesystem", "Navigieren"),
    ("wo bin ich", "filesystem", "PWD"),
    ("pwd", "filesystem", "PWD englisch"),
    ("tree", "filesystem", "Baum"),
    ("baum /Users/test", "filesystem", "Baum mit Pfad"),
    
    # Dateisystem-Operationen (README Zeile ~257-266)
    ("erstelle ordner projekt-2025", "filesystem", "Ordner erstellen"),
    ("verschiebe file.txt nach new.txt", "filesystem", "Verschieben"),
    ("kopiere source.pdf nach backup.pdf", "filesystem", "Kopieren"),
    
    # Organisation (README Zeile ~269-289)
    ("organisiere /Users/documents nach themen", "filesystem", "Nach Themen organisieren"),
    ("organisiere /Users/documents mit wissen", "filesystem", "Mit Wissen organisieren"),
    ("räume bitte auf", "filesystem", "Aufräumen"),
    ("räume auf den desktop", "filesystem", "Desktop aufräumen"),
    ("finde ähnliche dokumente zu /path/vertrag.pdf", "filesystem", "Ähnliche finden"),
    
    # Prioritäts-Tests (README Zeile ~580-585)
    ("wechsel zu /Users/test", "filesystem", "Wechsel MIT Pfad = Filesystem"),
    ("wechsel zu projekt-2025", "collection", "Wechsel OHNE Pfad = Collection"),
    
    # Begrüßungen (sollten NICHT als Commands erkannt werden)
    ("hallo", "greeting", "Begrüßung"),
    ("danke für die hilfe", "greeting", "Danke"),
    
    # Meta-Fragen (sollten NICHT als Commands erkannt werden, außer mit Pfad)
    ("was kannst du", "meta", "Meta-Frage"),
    # "was kannst du über X sagen" ist eine RAG-Frage, keine Filesystem-Operation
    ("was kannst du über /Users/test sagen", "rag", "Frage über Pfad = RAG"),
]


def get_route(query: str) -> str:
    """Bestimmt die Route für eine Query (wie im Chat-Loop)."""
    # Reihenfolge wie in cli.py chat()
    if is_greeting(query):
        return "greeting"
    
    fs = parse_filesystem_command(query)
    if fs:
        return "filesystem"
    
    coll = parse_collection_command(query)
    if coll:
        return "collection"
    
    idx = parse_index_command(query)
    if idx:
        return "index"
    
    if is_meta_question(query):
        return "meta"
    
    return "rag"


class TestReadmeChatExamples:
    """Testet alle README Chat-Beispiele."""
    
    @pytest.mark.parametrize("query,expected_route,description", README_CHAT_EXAMPLES)
    def test_readme_example(self, query: str, expected_route: str, description: str):
        """Prüft dass README-Beispiel korrekt geroutet wird."""
        actual_route = get_route(query)
        assert actual_route == expected_route, (
            f"README-Beispiel '{description}' fehlerhaft:\n"
            f"  Query: {query!r}\n"
            f"  Erwartet: {expected_route}\n"
            f"  Tatsächlich: {actual_route}"
        )


# ============================================================================
# CLI --help Konsistenz
# ============================================================================

EXPECTED_CLI_COMMANDS = ["chat", "collection", "health", "ingest", "search"]
EXPECTED_COLLECTION_SUBCOMMANDS = ["create", "delete", "info", "list", "use"]


class TestCliHelp:
    """Testet dass CLI-Commands existieren wie dokumentiert."""
    
    def test_main_commands_exist(self):
        """Prüft dass alle dokumentierten Haupt-Commands existieren."""
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"CLI --help fehlgeschlagen: {result.stderr}"
        
        for cmd in EXPECTED_CLI_COMMANDS:
            assert cmd in result.stdout, (
                f"Dokumentierter Command '{cmd}' fehlt in CLI --help:\n{result.stdout}"
            )
    
    def test_collection_subcommands_exist(self):
        """Prüft dass alle Collection-Subcommands existieren."""
        result = subprocess.run(
            [sys.executable, "-m", "src.cli", "collection", "--help"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"collection --help fehlgeschlagen: {result.stderr}"
        
        for cmd in EXPECTED_COLLECTION_SUBCOMMANDS:
            assert cmd in result.stdout, (
                f"Dokumentierter Collection-Subcommand '{cmd}' fehlt:\n{result.stdout}"
            )


# ============================================================================
# Parser-Spezifische Tests
# ============================================================================

class TestParserDetails:
    """Testet spezifische Parser-Details aus der Dokumentation."""
    
    def test_multiple_paths_takes_first(self):
        """README: 'indexiere /a und /b' nimmt nur /a"""
        result = parse_index_command("indexiere /Users/test und /Users/test2")
        assert result is not None
        assert result["path"] == "/Users/test", f"Erwartet /Users/test, bekam {result['path']}"
    
    def test_typo_correction_desktop(self):
        """README: Destop → Desktop wird korrigiert"""
        result = parse_filesystem_command("ls /Users/test/Destop")
        assert result is not None
        # Der Pfad sollte korrigiert sein (in extract_path_from_text)
        assert "Desktop" in str(result.get("path", "")) or "Destop" not in str(result.get("path", ""))
    
    def test_double_slash_normalization(self):
        """README: //Users//test → /Users/test"""
        result = parse_index_command("indexiere //Users//test")
        assert result is not None
        assert "//" not in result["path"], f"Doppelte Slashes nicht normalisiert: {result['path']}"
    
    def test_home_path_recognition(self):
        """README: ~/test wird erkannt, ~test nicht"""
        result_valid = parse_index_command("indexiere ~/test")
        assert result_valid is not None
        assert result_valid["path"] == "~/test"
        
        # ~test sollte NICHT als Pfad erkannt werden
        result_invalid = parse_index_command("indexiere ~test")
        # Entweder None oder der Pfad ist nicht ~test
        if result_invalid:
            assert result_invalid["path"] != "~test", "~test sollte nicht als Pfad erkannt werden"
    
    def test_organize_dry_run_default(self):
        """README: Organisation ist standardmäßig Vorschau (Dry-Run)"""
        result = parse_filesystem_command("organisiere /Users/test nach themen")
        assert result is not None
        assert result["action"] == "organize"
        # Der tidy-Flag sollte False sein für "nach themen"
        assert result.get("tidy") is False or result.get("tidy") is None
    
    def test_organize_with_jetzt_executes(self):
        """README: 'jetzt' am Ende führt aus"""
        result = parse_filesystem_command("organisiere /Users/test mit wissen jetzt")
        assert result is not None
        assert result["action"] == "organize"
        # Query sollte "jetzt" enthalten für Ausführung
        assert "jetzt" in result.get("query", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

