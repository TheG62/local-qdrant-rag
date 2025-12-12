#!/bin/bash
# install.sh - Vollständige Installation des Local Qdrant RAG Agent
#
# Verwendung:
#   chmod +x install.sh
#   ./install.sh
#
# Optionen:
#   --skip-docker    Docker/Qdrant nicht starten
#   --skip-ollama    Ollama Modell nicht laden
#   --model MODEL    Ollama Modell (default: qwen2.5:32b)

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default-Werte
SKIP_DOCKER=false
SKIP_OLLAMA=false
OLLAMA_MODEL="qwen2.5:32b"

# Parameter parsen
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --skip-ollama)
            SKIP_OLLAMA=true
            shift
            ;;
        --model)
            OLLAMA_MODEL="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}Unbekannte Option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}"
echo "════════════════════════════════════════════════════════════"
echo "       Local Qdrant RAG Agent - Installation"
echo "════════════════════════════════════════════════════════════"
echo -e "${NC}"

# 1. Python Version prüfen
echo -e "${YELLOW}[1/7] Prüfe Python Version...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        echo -e "${GREEN}  ✓ Python $PYTHON_VERSION gefunden${NC}"
    else
        echo -e "${RED}  ✗ Python 3.10+ benötigt (gefunden: $PYTHON_VERSION)${NC}"
        exit 1
    fi
else
    echo -e "${RED}  ✗ Python3 nicht gefunden${NC}"
    echo "  Bitte installieren: https://www.python.org/downloads/"
    exit 1
fi

# 2. Virtual Environment erstellen
echo -e "${YELLOW}[2/7] Erstelle Virtual Environment...${NC}"
if [ -d "venv" ]; then
    echo -e "${GREEN}  ✓ venv existiert bereits${NC}"
else
    python3 -m venv venv
    echo -e "${GREEN}  ✓ venv erstellt${NC}"
fi

# Aktivieren
source venv/bin/activate
echo -e "${GREEN}  ✓ venv aktiviert${NC}"

# 3. Dependencies installieren
echo -e "${YELLOW}[3/7] Installiere Python Dependencies...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}  ✓ Dependencies installiert${NC}"

# Hinweis: Docling lädt beim ersten Start Modelle herunter
echo -e "${BLUE}  ℹ Docling wird beim ersten Start zusätzliche Modelle laden (~1GB)${NC}"

# 4. .env erstellen
echo -e "${YELLOW}[4/7] Erstelle Konfiguration...${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}  ✓ .env existiert bereits${NC}"
else
    cp .env.example .env
    # Modell in .env setzen falls nicht default
    if [ "$OLLAMA_MODEL" != "qwen2.5:32b" ]; then
        sed -i.bak "s/OLLAMA_MODEL=.*/OLLAMA_MODEL=$OLLAMA_MODEL/" .env 2>/dev/null || \
        sed -i '' "s/OLLAMA_MODEL=.*/OLLAMA_MODEL=$OLLAMA_MODEL/" .env
    fi
    echo -e "${GREEN}  ✓ .env erstellt (Modell: $OLLAMA_MODEL)${NC}"
fi

# 5. Docker/Qdrant starten
echo -e "${YELLOW}[5/7] Starte Qdrant (Docker)...${NC}"
if $SKIP_DOCKER; then
    echo -e "${BLUE}  ⏭ Übersprungen (--skip-docker)${NC}"
else
    if command -v docker &> /dev/null; then
        if docker info &> /dev/null; then
            docker compose up -d
            echo -e "${GREEN}  ✓ Qdrant gestartet${NC}"
            
            # Warten bis Qdrant bereit ist
            echo -e "${BLUE}  ⏳ Warte auf Qdrant...${NC}"
            for i in {1..30}; do
                if curl -s http://localhost:6333/health > /dev/null 2>&1; then
                    echo -e "${GREEN}  ✓ Qdrant ist bereit${NC}"
                    break
                fi
                sleep 1
            done
        else
            echo -e "${RED}  ✗ Docker läuft nicht${NC}"
            echo "  Bitte Docker Desktop starten und erneut ausführen"
        fi
    else
        echo -e "${RED}  ✗ Docker nicht installiert${NC}"
        echo "  Bitte installieren: https://www.docker.com/products/docker-desktop/"
    fi
fi

# 6. Ollama Modell laden
echo -e "${YELLOW}[6/7] Lade Ollama Modell...${NC}"
if $SKIP_OLLAMA; then
    echo -e "${BLUE}  ⏭ Übersprungen (--skip-ollama)${NC}"
else
    if command -v ollama &> /dev/null; then
        # Prüfen ob Ollama läuft
        if ! pgrep -x "ollama" > /dev/null && ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
            echo -e "${BLUE}  ⏳ Starte Ollama...${NC}"
            ollama serve &> /dev/null &
            sleep 3
        fi
        
        # Prüfen ob Modell existiert
        if ollama list | grep -q "$OLLAMA_MODEL"; then
            echo -e "${GREEN}  ✓ Modell $OLLAMA_MODEL bereits vorhanden${NC}"
        else
            echo -e "${BLUE}  ⏳ Lade $OLLAMA_MODEL (kann einige Minuten dauern)...${NC}"
            ollama pull "$OLLAMA_MODEL"
            echo -e "${GREEN}  ✓ Modell $OLLAMA_MODEL geladen${NC}"
        fi
    else
        echo -e "${RED}  ✗ Ollama nicht installiert${NC}"
        echo "  Bitte installieren: https://ollama.ai"
    fi
fi

# 7. Health Check
echo -e "${YELLOW}[7/7] Führe Health Check durch...${NC}"
sleep 2
python -m src.cli health

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════"
echo "  ✅ Installation abgeschlossen!"
echo "════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Nächste Schritte:"
echo ""
echo "  1. Virtual Environment aktivieren (falls noch nicht):"
echo -e "     ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "  2. Dokumente indexieren:"
echo -e "     ${BLUE}python -m src.cli ingest -d ./documents -r${NC}"
echo ""
echo "  3. Chat starten:"
echo -e "     ${BLUE}python -m src.cli chat --show-sources${NC}"
echo ""
echo "Für schwächere Hardware (16GB RAM):"
echo -e "  ${BLUE}./install.sh --model qwen2.5:7b${NC}"
echo ""
