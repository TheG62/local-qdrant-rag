# OpenWebUI Setup Guide

## ✅ API-Server Status

Die API funktioniert korrekt! Alle Endpoints sind erreichbar und kompatibel.

## 🔧 Schritt-für-Schritt Setup

### 1. API-Server starten

```bash
cd /Users/guneyyilmaz/local-qdrant-rag
source venv/bin/activate
python -m src.cli serve
```

**WICHTIG:** Notiere dir den Port aus der Ausgabe (z.B. `8001`)

### 2. OpenWebUI öffnen

Öffne OpenWebUI in deinem Browser (normalerweise `http://localhost:3000`)

### 3. Connection hinzufügen

1. Gehe zu **Settings** (⚙️ oben rechts)
2. Klicke auf **Connections** (oder **Connections & Models**)
3. Klicke auf **+ Add Connection** oder **+ New Connection**
4. Wähle **OpenAI** als Provider

### 4. Konfiguration ausfüllen

**Base URL:**
```
http://localhost:8001/v1
```
⚠️ **WICHTIG:** Muss mit `/v1` enden! Nicht `http://localhost:8001`

**API Key:**
```
local-rag
```
(oder beliebiger Text - wird nicht validiert)

**Model:**
```
local-rag
```
⚠️ **WICHTIG:** Muss genau `local-rag` sein (nicht `qwen2.5:32b`)

### 5. Testen

1. Klicke auf **Test Connection** oder **Save**
2. Erstelle einen neuen Chat
3. Wähle die Connection aus (sollte als "local-rag" erscheinen)
4. Stelle eine Frage

## 🔍 Troubleshooting

### Problem: "Connection refused"

**Lösung:**
- Prüfe ob Server läuft: `curl http://localhost:8001/health`
- Prüfe Port in Base URL (muss mit Server-Output übereinstimmen)
- Prüfe ob `/v1` am Ende der Base URL steht

### Problem: "Model not found"

**Lösung:**
- Model muss genau `local-rag` sein
- Prüfe Models: `curl http://localhost:8001/v1/models`
- Stelle sicher, dass `local-rag` in der Liste ist

### Problem: "Invalid API key"

**Lösung:**
- API Key wird nicht validiert - jeder Wert funktioniert
- Versuche einen anderen Wert (z.B. `test`, `local`, `rag`)

### Problem: Keine Antwort / Timeout

**Lösung:**
- Prüfe Server-Logs für Fehler
- Prüfe ob Ollama läuft: `ollama list`
- Prüfe ob Qdrant läuft: `docker ps`

### Problem: CORS-Fehler im Browser

**Lösung:**
- Die API hat CORS aktiviert
- Falls trotzdem Probleme: Prüfe Browser-Console
- Stelle sicher, dass OpenWebUI und API auf demselben Host laufen

## 🧪 Diagnose-Script

Falls es weiterhin nicht funktioniert, führe das Diagnose-Script aus:

```bash
python test_openwebui_connection.py
```

Das Script prüft:
- ✅ Health Check
- ✅ Models Endpoint
- ✅ Chat Endpoint (non-streaming)
- ✅ Chat Endpoint (streaming)
- ✅ CORS Headers

## 📋 Checkliste

- [ ] API-Server läuft (`python -m src.cli serve`)
- [ ] Port notiert (z.B. 8001)
- [ ] Base URL: `http://localhost:PORT/v1` (mit `/v1`!)
- [ ] API Key: beliebig (z.B. `local-rag`)
- [ ] Model: `local-rag` (nicht `qwen2.5:32b`)
- [ ] Connection in OpenWebUI gespeichert
- [ ] Chat erstellt und Connection ausgewählt

## 🎯 Beispiel-Konfiguration

```
Provider: OpenAI
Base URL: http://localhost:8001/v1
API Key: local-rag
Model: local-rag
```

## 💡 Tipps

1. **Port ändern:** Falls Port 8001 belegt ist, starte mit `python -m src.cli serve --port 9000`
2. **Server neu starten:** Falls Änderungen nicht übernommen werden, starte Server neu
3. **Browser-Console prüfen:** Öffne Developer Tools (F12) → Console für Fehler
4. **Server-Logs prüfen:** Schau in das Terminal wo der Server läuft für Fehlermeldungen

