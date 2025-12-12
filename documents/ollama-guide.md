# Ollama Deployment Guide

## Installation auf macOS

Ollama läuft nativ auf macOS und nutzt die Apple Silicon GPU (MPS) für beschleunigte Inferenz.

### Voraussetzungen

- macOS 12 oder neuer
- Apple Silicon (M1, M2, M3) oder Intel Mac
- Mindestens 8GB RAM (16GB+ empfohlen für größere Modelle)

### Installation

```bash
brew install ollama
```

Oder Download von ollama.ai

## Modelle

### Empfohlene Modelle für RAG

| Modell | Größe | VRAM | Use Case |
|--------|-------|------|----------|
| qwen2.5:7b | 4.7GB | 8GB | Schnelle Inferenz |
| qwen2.5:32b | 19GB | 24GB | Beste Balance |
| llama3.1:70b | 40GB | 48GB | Maximale Qualität |

### Modell herunterladen

```bash
ollama pull qwen2.5:32b
```

## API Endpunkte

Ollama bietet eine OpenAI-kompatible API:

- Chat Completions: `POST /api/chat`
- Embeddings: `POST /api/embeddings`
- Generate: `POST /api/generate`

Standard-Port: 11434

## Mac Studio M3 Ultra Optimierung

Der Mac Studio M3 Ultra mit 192GB Unified Memory kann auch das 70B Modell komfortabel ausführen. Für parallele Embedding-Generierung und LLM-Inferenz empfehlen wir:

- qwen2.5:32b als Primary Model
- Ausreichend Headroom für sentence-transformers
