# Local Qdrant RAG Agent 🤖

Ein vollständig lokaler RAG-Assistent (Retrieval Augmented Generation) für deutsche Unternehmen. **100% GDPR-konform** - alle Daten bleiben auf Ihrer Infrastruktur.

![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Local First](https://img.shields.io/badge/Local-First-orange.svg)

## ✨ Features

### Kernfunktionen
- 🔒 **100% Lokal** - Keine Cloud-Abhängigkeiten, keine Daten verlassen Ihr Netzwerk
- 🇩🇪 **Deutschsprachig** - Optimiert für deutsche Texte und Antworten
- 📄 **Docling-powered** - IBM's Document Understanding für komplexe Dokumente
- 🔍 **Hybrid Search** - Kombiniert semantische Suche mit Volltextsuche (RRF-Merge)
- ⚡ **Streaming** - Antworten werden Wort für Wort angezeigt
- 🌐 **OpenAI-kompatible API** - Integration mit OpenWebUI, Continue.dev und anderen Tools

### Dokumentverarbeitung
| Format | Features |
|--------|----------|
| PDF | Komplexe Layouts, Tabellen, OCR für gescannte Docs |
| Word (.docx) | Formatierung, Tabellen, Styles |
| PowerPoint (.pptx) | Folien, Notizen |
| Excel (.xlsx) | Sheets, Formeln (als Werte) |
| HTML/Markdown | Struktur-erhaltend |
| Images | OCR für PNG, JPG, TIFF |

### Intelligente Befehle
- **Chat-basierte Indexierung**: `indexiere ~/Desktop/Dokumente`
- **Dateisystem-Navigation**: `ls`, `cd`, `tree`, `pwd`
- **Datei-Operationen**: Erstellen, Verschieben, Kopieren, Löschen
- **Multi-Collection**: Mehrere Wissensdatenbanken verwalten
- **ERP-ähnliche Organisation**: Dokumente automatisch nach Kunden/Projekten sortieren

## 🚀 Quickstart

### Voraussetzungen

- Python 3.10+
- Docker (für Qdrant)
- [Ollama](https://ollama.ai) installiert
- ~8GB freier Speicherplatz

### Installation

```bash
# 1. Repository klonen
git clone https://github.com/YOUR_USERNAME/local-qdrant-rag.git
cd local-qdrant-rag

# 2. Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/macOS
# oder: venv\Scripts\activate  # Windows

# 3. Dependencies installieren
pip install -r requirements.txt

# 4. Konfiguration
cp .env.example .env
# Optional: .env anpassen

# 5. Qdrant starten
docker compose up -d

# 6. Ollama-Modell laden
ollama pull qwen2.5:32b
# Oder für schwächere Hardware: ollama pull qwen2.5:7b
```

### Erster Test

```bash
# Health Check
python -m src.cli health

# Dokumente indexieren
python -m src.cli ingest -d ./documents -r

# Chat starten
python -m src.cli chat --show-sources
```

## 💬 Chat-Befehle

### Indexierung
```
indexiere /pfad/zum/ordner
indexiere ~/Desktop -r          # rekursiv
füge /pfad hinzu
```

### Wissensdatenbanken
```
erstelle wissensdatenbank projekt-2025
zeige alle wissensdatenbanken
wechsel zu projekt-2025
lösche wissensdatenbank test
```

### Dateisystem
```
ls /pfad                        # Verzeichnis anzeigen
cd ~/Desktop                    # Navigieren
pwd                             # Aktuelles Verzeichnis
tree /pfad                      # Baumstruktur
erstelle ordner neuer_ordner
verschiebe alt.txt nach neu.txt
```

### Organisation
```
organisiere ~/Desktop nach themen           # Themen-basiert
organisiere ~/Dokumente mit wissen          # ERP-ähnlich (Kunden/Projekte)
räume auf den desktop                       # Quick-Tidy
finde ähnliche dokumente zu /pfad/doc.pdf
```

### Fragen
```
Was macht TimeSkipCom?
Erkläre mir die RAG-Architektur
Fasse den Vertrag zusammen
```

## 🌐 API Server (OpenWebUI Integration)

Der RAG-Agent kann als OpenAI-kompatibler API-Server gestartet werden, um mit Tools wie **OpenWebUI**, **Continue.dev** oder anderen OpenAI-kompatiblen Clients zu funktionieren.

### Server starten

```bash
# Via CLI (findet automatisch freien Port)
python -m src.cli serve

# Mit bestimmtem Port
python -m src.cli serve --port 9000

# Oder direkt via uvicorn
python -m uvicorn src.api:app --host 0.0.0.0 --port 8001
```

> **Hinweis:** Der Server prüft automatisch ob der gewünschte Port frei ist und sucht bei Bedarf einen freien Port. Default-Port ist 8001.

### OpenWebUI konfigurieren

1. Öffne OpenWebUI Settings → Connections
2. Füge eine neue OpenAI-Connection hinzu:
   - **Base URL**: `http://localhost:PORT/v1` (PORT aus Server-Output)
   - **API Key**: beliebig (z.B. `local-rag`)
3. Wähle das Model `local-rag` aus

### API Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/v1/chat/completions` | POST | OpenAI-kompatibler Chat (mit RAG) |
| `/v1/models` | GET | Verfügbare Modelle |
| `/v1/rag/search` | POST | Direkte RAG-Suche ohne LLM |
| `/v1/rag/collections` | GET | Qdrant Collections auflisten |
| `/health` | GET | Health-Check |
| `/docs` | GET | Swagger UI Dokumentation |

### Beispiel: Chat mit cURL

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-rag",
    "messages": [{"role": "user", "content": "Was ist RAG?"}],
    "stream": false
  }'
```

### RAG deaktivieren

Falls du die RAG-Suche für einzelne Anfragen deaktivieren möchtest:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-rag",
    "messages": [{"role": "user", "content": "Hallo!"}],
    "use_rag": false
  }'
```

## ⚙️ Konfiguration

Alle Einstellungen über `.env` oder Umgebungsvariablen:

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant Server |
| `OLLAMA_MODEL` | `qwen2.5:32b` | LLM Modell |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Embedding Modell |
| `EMBEDDING_DIMENSION` | `1024` | Embedding Dimension |
| `CHUNK_SIZE` | `1000` | Max Tokens pro Chunk |
| `TOP_K` | `10` | Suchergebnisse |
| `RRF_K` | `60` | RRF Konstante |
| `MIN_SCORE` | `0.01` | Minimaler Relevanz-Score |
| `RETRIEVAL_STRATEGY` | `hybrid_rrf` | Such-Strategie |

## 🏗️ Architektur

```
Chat-Eingabe
    │
    ├─► Greeting? → Kurze Antwort
    │
    ├─► Meta-Frage? → Selbstbeschreibung + Collection-Info
    │
    ├─► Filesystem-Befehl? → Navigator/Operations/Organizer
    │       ├─► ls, cd, pwd, tree
    │       ├─► mkdir, mv, cp, rm
    │       └─► organisiere (Themen/Wissen)
    │
    ├─► Collection-Befehl? → Collection Manager
    │
    ├─► Index-Befehl? → Docling Pipeline
    │
    └─► Inhaltsfrage? → RAG (Hybrid-Suche → Ollama)
```

### Tech Stack

- **Vector DB**: Qdrant (lokal via Docker)
- **LLM**: Ollama (qwen2.5, llama3.1)
- **Embeddings**: BGE-M3 (multilingual, 1024 dim)
- **Dokumente**: Docling (IBM)
- **Suche**: Hybrid RRF (Semantic + Fulltext)
- **API**: FastAPI (OpenAI-kompatibel)

## 💻 Hardware-Empfehlungen

| Setup | RAM | Modell | Bemerkung |
|-------|-----|--------|-----------|
| Minimal | 16GB | qwen2.5:7b | Funktional |
| Standard | 32GB | qwen2.5:14b | Gute Balance |
| Empfohlen | 64GB | qwen2.5:32b | Beste Qualität |
| High-End | 128GB+ | llama3.1:70b | Maximum |

> Apple Silicon (M1/M2/M3/M4) nutzt automatisch MPS für GPU-Beschleunigung.

## 🧪 Tests

```bash
# Pattern-Tests
python tests/test_patterns.py

# Filesystem-Tests
python test_filesystem_functions.py

# System Health Check
python system_health_check.py
```

## 📁 Projektstruktur

```
local-qdrant-rag/
├── src/
│   ├── cli.py                  # CLI + Chat Interface
│   ├── api.py                  # OpenAI-kompatible REST API
│   ├── settings.py             # Konfiguration
│   ├── tools.py                # Search Tools
│   ├── ingestion/              # Docling Pipeline
│   │   ├── document_loader.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   └── ingest.py
│   ├── retrieval/              # Hybrid Search
│   │   ├── semantic.py
│   │   ├── fulltext.py
│   │   └── hybrid_rrf.py
│   ├── vectorstore/            # Qdrant Integration
│   │   ├── qdrant_client.py
│   │   ├── schema.py
│   │   └── collection_manager.py
│   ├── filesystem/             # Dateisystem-Operationen
│   │   ├── navigator.py
│   │   ├── operations.py
│   │   ├── organizer.py
│   │   └── knowledge_organizer.py
│   └── providers/
│       └── ollama_provider.py
├── tests/
│   └── test_patterns.py
├── documents/                  # Beispiel-Dokumente
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## 🔧 Troubleshooting

### Qdrant nicht erreichbar
```bash
docker ps                    # Container Status
docker compose down
docker compose up -d
docker compose logs qdrant   # Logs prüfen
```

### Ollama nicht erreichbar
```bash
ollama serve                 # Service starten
ollama list                  # Modelle prüfen
ollama pull qwen2.5:32b      # Modell laden
```

### Docling Download langsam
```bash
# Manueller Download der Modelle
python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"
```

### Out of Memory
- Kleineres LLM: `OLLAMA_MODEL=qwen2.5:7b`
- `CHUNK_SIZE` reduzieren
- `TOP_K` reduzieren

### OpenWebUI Verbindungsprobleme

**Problem: "Connection refused" oder "Model not found"**

1. **Prüfe ob der API-Server läuft:**
   ```bash
   curl http://localhost:8001/health
   # Sollte {"status":"ok",...} zurückgeben
   ```

2. **Prüfe die Base URL in OpenWebUI:**
   - Base URL muss sein: `http://localhost:PORT/v1` (mit `/v1` am Ende!)
   - PORT ist der Port aus dem Server-Output (z.B. 8001)
   - **WICHTIG:** Nicht `http://localhost:8001` sondern `http://localhost:8001/v1`

3. **Prüfe ob das Model verfügbar ist:**
   ```bash
   curl http://localhost:8001/v1/models
   # Sollte "local-rag" in der Liste sein
   ```

4. **Teste die API direkt:**
   ```bash
   curl http://localhost:8001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer test" \
     -d '{
       "model": "local-rag",
       "messages": [{"role": "user", "content": "test"}]
     }'
   ```

5. **Häufige Fehler:**
   - ❌ Base URL: `http://localhost:8001` → ✅ `http://localhost:8001/v1`
   - ❌ Port falsch → Prüfe Server-Output für tatsächlichen Port
   - ❌ Server nicht gestartet → `python -m src.cli serve`
   - ❌ Falsches Model → Muss `local-rag` sein (nicht `qwen2.5:32b`)

6. **CORS-Probleme:**
   - Die API hat CORS aktiviert (`allow_origins=["*"]`)
   - Falls trotzdem Probleme: Prüfe Browser-Console für CORS-Fehler
   - Stelle sicher, dass OpenWebUI und API-Server auf demselben Host laufen

7. **Streaming-Probleme:**
   - OpenWebUI nutzt standardmäßig Streaming
   - Falls Probleme: Prüfe Server-Logs für Fehler
   - Teste mit `"stream": false` in der API direkt

## 📝 Changelog

Siehe [CHANGELOG.md](CHANGELOG.md) für alle Änderungen.

## 🤝 Contributing

Contributions sind willkommen! Bitte:

1. Fork das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Commit deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE) für Details.

## 🙏 Attribution

Ursprünglich basierend auf [MongoDB-RAG-Agent](https://github.com/coleam00/MongoDB-RAG-Agent) von Cole Medin, vollständig umgeschrieben für lokalen Betrieb mit Qdrant, Docling und Ollama.

---

Entwickelt von **TimeSkipCom** für GDPR-konforme AI-Lösungen in deutschen Unternehmen.
