# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-12-12

### Added
- **Pattern-Verbesserungen und Sicherheit**:
  - Verbesserte Pfad-Extraktion mit Priorität für absolute Pfade
  - Path Traversal Erkennung: `/Users/../../../etc/passwd` wird vollständig erkannt
  - Tippfehler-Korrektur: Automatische Korrektur von `Destop` → `Desktop`
  - Command Priority: Collection-Befehle haben Priorität vor Filesystem-Befehlen
  - Mehrere Befehle: Stoppt beim ersten "und" oder "dann" und nimmt nur den ersten Pfad/Befehl
  - Verbesserte Greeting-Erkennung: "danke für die hilfe" wird erkannt
  - Meta Question False Positives: Pfade verhindern fälschliche Meta-Fragen
  - Doppelte Slashes werden normalisiert: `//Users//test` → `/Users/test`
  - Home-Pfad Erkennung: `~/test` wird erkannt, `~test` nicht
- **Intelligente Chat-Befehle**: Indexierungs-Befehle können direkt im Chat verwendet werden
  - Unterstützt natürliche Befehle: `indexiere`, `lade`, `importiere`, `füge hinzu`, `lerne`
  - Versteht Floskeln wie "bitte", "den gesamten inhalt" automatisch
  - Robuste Pfad-Erkennung für absolute, relative und Home-Pfade
- **Automatische Rekursion**: Erkennt automatisch wenn keine Dateien im Root-Verzeichnis sind und sucht rekursiv
- **Pattern-Erkennung**: 
  - Erkennt Begrüßungen und Small-Talk
  - Erkennt Meta-Fragen über den Agent
  - Separate System-Prompts für verschiedene Kontexte
- **Verbesserte Pfad-Extraktion**: Neue `extract_path_from_text` Funktion für robuste Pfad-Erkennung
- **Collection-Management**: Vollständige Verwaltung von Qdrant Collections
  - Erstellen, Auflisten, Löschen, Wechseln von Collections
  - CLI-Befehle und Chat-Integration
  - Schutz für Standard-Collection
- **Dateisystem-Navigation**: Vollständige Verzeichnis-Navigation im Chat
  - `ls`, `cd`, `pwd`, `tree` Befehle
  - Verzeichnisinhalt anzeigen und navigieren
  - Verzeichnisstruktur visualisieren
- **Dateisystem-Operationen**: Datei- und Ordner-Management
  - Erstellen von Ordnern und Dateien
  - Verschieben, Kopieren, Löschen
  - Sicherheitsabfragen für destruktive Operationen
- **Sichere Organisations-Workflows (Default Preview)**:
  - `organisiere ... nach themen` und `organisiere ... mit wissen` laufen standardmäßig als **Vorschau (dry_run)**
  - Ausführung erst mit expliziter Bestätigung per „jetzt“
  - „räume auf …“ bleibt ein schneller, sicherer Top-Level Modus (ebenfalls Vorschau default)
- **Intelligente Dokument-Organisation**: Basierend auf Docling + Hybrid-Suche
  - `organize_by_themes()` - Organisiert Dokumente nach Themen in Ordnerstruktur
  - `find_similar_documents()` - Findet ähnliche Dokumente mit Hybrid-Suche
  - Nutzt Docling für Dokumentverarbeitung und Embeddings für Ähnlichkeitsanalyse
- **ERP-ähnliche Organisation mit indexiertem Wissen**: 
  - `suggest_organization_structure()` - Schlägt Organisations-Struktur vor basierend auf indexiertem Wissen
  - `organize_with_knowledge()` - Organisiert Dokumente ERP-ähnlich (Kunden/Projekte-Struktur)
  - Erkennt automatisch: Kunden, Projekte, Verträge, Rechnungen, Angebote
  - Extrahiert Entitäten (Kunden-Namen, Projekt-Namen) aus Dokumenten
  - Erstellt strukturierte Ordnerhierarchie: `Kunden/Kunde_A/Verträge/`
  - Nutzt Hybrid-Suche um ähnliche Dokumente im indexierten Wissen zu finden
  - Zeigt Vorschläge vor der Organisation
- **Erweiterte Dokumentation**: README mit allen neuen Features und Beispielen aktualisiert
- **System Health Check**: Umfassendes Health-Check-Script für alle Komponenten

### Changed
- **Verbesserte `parse_index_command` Funktion**: 
  - Spezielle Behandlung für "füge X hinzu" Pattern
  - Bessere Erkennung von relativen Pfaden
  - Entfernt Floskeln automatisch
- **Intelligente `execute_indexing` Funktion**: 
  - Prüft automatisch ob Dateien im Root-Verzeichnis vorhanden sind
  - Aktiviert automatisch rekursive Suche wenn nötig
  - Informative Statusmeldungen
- **Chat-Integration**: Erweitert um Dateisystem- und Collection-Befehle
  - Priorität: **Wenn Pfad vorhanden → Dateisystem**, sonst **Collection → Indexierung → RAG**
  - Natürliche Befehle für alle Operationen

### Fixed
- Pfad-Erkennung funktioniert jetzt auch mit Floskeln wie "bitte den gesamten inhalt"
- Relative Pfade werden korrekt erkannt (z.B. `./documents`)
- "füge /path hinzu" Pattern wird korrekt geparst
- macOS Symlink-Handling (`/var` → `/private/var`) in Navigation
- **Pattern-Verbesserungen**:
  - Path Traversal wird vollständig erkannt (nicht nur relativer Teil)
  - Absolute Pfade haben Priorität vor relativen Pfaden in der Extraktion
  - Command Priority funktioniert korrekt (Pfad → Filesystem, sonst Collection → Index → RAG)
  - Mehrere Pfade in einem Befehl werden korrekt behandelt (nur erster wird genommen)
  - Greeting Pattern erkennt jetzt auch "danke für die hilfe"
  - Meta Questions mit Pfaden werden nicht mehr fälschlich erkannt
  - Doppelte Slashes werden normalisiert
  - Home-Pfade werden korrekt unterschieden (`~/test` vs `~test`)

## [0.4.0] - 2025-02-11
### Added
- **Dynamic Database & Collection Selection**: Users can now specify databases and collections dynamically at query time.
- **Expanded Documentation**: Updated README with step-by-step instructions from setup to implementation.
- **Updated Usage Examples**: `basic-usage.js` and `advanced-usage.js` now demonstrate dynamic database selection.
- **Enhanced Logging**: MongoRAG now logs database/collection selection during operations for better debugging.

### Changed
- **Refactored MongoRAG Connection Handling**: Ensures database and collection are dynamically set without breaking existing functionality.
- **Improved Tests**: Added new tests for dynamic selection and enhanced validation checks.

## [1.1.0] - 2025-02-11
### Changed
- Implemented **semantic chunking** using the `natural.SentenceTokenizer` to split documents into meaningful sentence chunks.
- Implemented **recursive chunking** that splits paragraphs first, and if sections are too large, further splits by sentences.
- Enhanced **sliding window** chunking to preserve overlap between chunks.

### Fixed
- Fixed document chunking strategies to provide more meaningful and efficient chunking based on document content.

## [1.0.0] - 2025-02-01
### Initial release
- Initial version with basic chunking functionality (sliding window strategy).

