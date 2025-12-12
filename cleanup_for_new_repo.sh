#!/bin/bash
# cleanup_for_new_repo.sh
# Bereinigt das Projekt für ein neues Git-Repository
# 
# Führe aus mit: ./cleanup_for_new_repo.sh
# Oder zur Vorschau: ./cleanup_for_new_repo.sh --dry-run

set -e

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🔍 DRY RUN - Keine Dateien werden gelöscht"
    echo ""
fi

echo "════════════════════════════════════════════════════════════"
echo "CLEANUP FÜR NEUES REPOSITORY"
echo "════════════════════════════════════════════════════════════"
echo ""

# Funktion zum sicheren Löschen
safe_remove() {
    local path="$1"
    if [ -e "$path" ]; then
        if $DRY_RUN; then
            echo "  [würde löschen] $path"
        else
            rm -rf "$path"
            echo "  ✓ Gelöscht: $path"
        fi
    fi
}

# 1. Temporäre Test-Verzeichnisse
echo "1. Temporäre Test-Verzeichnisse..."
safe_remove "tmp_erp_test"
safe_remove "tmp_erp_test_organisiert_wissen"
safe_remove "tmp_fs_ops"
safe_remove "tmp_index_nested"
safe_remove "tmp_tidy_test"
safe_remove "tmp_tidy_test_aufgeraeumt"

# 2. Python Caches
echo ""
echo "2. Python Caches..."
if $DRY_RUN; then
    echo "  [würde löschen] __pycache__/, .pytest_cache/, *.pyc"
else
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    echo "  ✓ Python Caches gelöscht"
fi

# 3. Legacy MongoDB-RAG Dateien (Root-Level)
echo ""
echo "3. Legacy MongoDB-RAG Dateien (Root)..."
safe_remove "mongodb-rag-docs"
safe_remove "bin"
safe_remove "examples"
safe_remove "static"
safe_remove "favicon.ico"
safe_remove "package.json"
safe_remove "jest-config.js"
safe_remove "jest-setup.js"
safe_remove "release-alpha.js"
safe_remove "test-ingest.js"
safe_remove ".eslint.json"

# 4. Legacy MongoDB-RAG Dateien (src/)
echo ""
echo "4. Legacy MongoDB-RAG Dateien (src/)..."
safe_remove "src/index.js"
safe_remove "src/playground-ui"
safe_remove "src/cli"
safe_remove "src/core"

# 5. Legacy Test-Dateien
echo ""
echo "5. Legacy Test-Dateien..."
safe_remove "test"
safe_remove "tests/cli.test.js"
safe_remove "tests/commands"

# 6. IDE Caches
echo ""
echo "6. IDE Caches..."
safe_remove ".cursor"

# 7. Logs
echo ""
echo "7. Log-Dateien..."
if $DRY_RUN; then
    echo "  [würde löschen] *.log"
else
    find . -name "*.log" -type f -delete 2>/dev/null || true
    echo "  ✓ Log-Dateien gelöscht"
fi

# 8. Unnötige Dokumentation
echo ""
echo "8. Unnötige Dokumentation..."
safe_remove "DEVELOPER.md"
safe_remove ".aidigestignore"

# 9. GitHub Actions (prüfen ob aktuell)
echo ""
echo "9. GitHub Actions..."
if [ -d ".github" ]; then
    if $DRY_RUN; then
        echo "  [vorhanden] .github/ - manuell prüfen ob Workflows aktuell"
    else
        echo "  ⚠️ .github/ vorhanden - manuell prüfen ob Workflows aktuell"
    fi
fi

# 10. Cleanup-Script selbst entfernen (optional)
echo ""
echo "10. Setup-Dateien..."
safe_remove "REPO_SETUP.md"
# cleanup_for_new_repo.sh bleibt für spätere Nutzung

echo ""
echo "════════════════════════════════════════════════════════════"
echo "ZUSAMMENFASSUNG"
echo "════════════════════════════════════════════════════════════"

if $DRY_RUN; then
    echo ""
    echo "🔍 Dies war eine Vorschau. Um wirklich zu löschen:"
    echo "   ./cleanup_for_new_repo.sh"
else
    echo ""
    echo "✅ Cleanup abgeschlossen!"
    echo ""
    echo "Verbleibende Struktur:"
    echo "  src/"
    echo "    ├── cli.py"
    echo "    ├── settings.py"
    echo "    ├── tools.py"
    echo "    ├── ingestion/"
    echo "    ├── retrieval/"
    echo "    ├── vectorstore/"
    echo "    ├── filesystem/"
    echo "    └── providers/"
    echo "  tests/"
    echo "  documents/"
    echo "  docker-compose.yml"
    echo "  requirements.txt"
    echo "  pyproject.toml"
    echo "  README.md"
    echo "  CHANGELOG.md"
    echo "  LICENSE"
    echo "  .env.example"
    echo "  .gitignore"
    echo ""
    echo "Nächste Schritte:"
    echo ""
    echo "1. Altes Git-Repository entfernen:"
    echo "   rm -rf .git"
    echo ""
    echo "2. Neues Repository initialisieren:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit: Local Qdrant RAG Agent v1.0.0'"
    echo ""
    echo "3. Remote hinzufügen:"
    echo "   git remote add origin https://github.com/USERNAME/REPO.git"
    echo "   git push -u origin main"
fi
