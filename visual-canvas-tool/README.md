# Visual Canvas Tool

Ein **visuelles Canvas- und Kollaborationswerkzeug** (Milanote-orientiert) — als
DSGVO-konformer, EU-/self-host-fähiger Klon umgesetzt gemäß **Lastenheft v1.0**
und **Pflichtenheft v1.0**.

Diese Implementierung ist ein **lauffähiger MVP**, der alle `MUSS`-Kriterien des
Lastenhefts abbildet und die Architekturprinzipien des Pflichtenhefts
(Local-first/CRDT, DSGVO-by-Design, permissive Lizenzen, Modularität,
SaaS + Self-Hosting) konkret umsetzt.

---

## Funktionsumfang (MVP)

| Lastenheft | Umgesetzt |
|-----------|-----------|
| /MK10/ Unendlicher Canvas, Drag-&-Drop | ✅ Zoom/Pan via CSS-Transform, freie Platzierung |
| /MK20/ Mehrere Kartentypen | ✅ Notiz, Bild, Link (mit Vorschau), To-do, Spalte, Farbfeld |
| /MK30/ Verschachtelte Boards + Home-Board | ✅ Sub-Boards, Home-Board, Board-Verknüpfungskarten |
| /MK40/ Echtzeit-Co-Editing + Kommentare | ✅ Yjs-CRDT, Presence/Cursor, Inline-Kommentare |
| /MK50/ Teilen (Rechte + öffentlicher Lese-Link) | ✅ Einladung Bearbeiter/Betrachter, public read-only Token |
| /MK60/ Volltextsuche | ✅ Suche über Boardtitel + Canvas-Inhalt |
| /MK70/ DSGVO-konform, EU-hostbar | ✅ EU-Self-Host, Export/Löschung, lokale Datenhaltung |
| /MK80/ Web-Anwendung | ✅ React-SPA |
| /F500/ Verbindungslinien | ✅ Bézier-Verbindungen, folgen Karten (/F520/) |
| /F430/,/R70/ Aktivitätsprotokoll | ✅ Audit-/Activity-Log |
| /F830/,/R40/ Datenexport + Konto-Löschung | ✅ JSON-Export, Recht auf Vergessenwerden |
| /WK90/,/T130/ Self-Hosting | ✅ Docker-Compose-Paket |

> Hinweis: Dies ist eine MVP-Referenzimplementierung. Der vollständige
> Produktions-Stack des Pflichtenhets (NestJS, PostgreSQL, S3-Objektspeicher,
> Keycloak/SSO, Meilisearch, TipTap) ist als **Ausbaupfad** unten dokumentiert.
> Die Modulgrenzen sind bewusst so gezogen, dass diese Bausteine austauschbar sind.

---

## Architektur

```
┌─────────────────────────────┐        ┌──────────────────────────────┐
│  apps/web  (React + TS)      │        │  apps/server (Node + TS)     │
│  - DOM-Canvas (Zoom/Pan)     │ REST   │  - Express REST-API          │
│  - Kartentypen / Editoren    │◄──────►│    (Auth, Boards, Freigaben, │
│  - Yjs-Client (y-websocket)  │  WS    │     Suche, Export, Proxy)    │
│  - Presence / Kommentare     │◄──────►│  - Yjs-Sync (y-protocols/ws) │
└─────────────────────────────┘        │  - Persistenz (JSON+Snapshot)│
                                        └──────────────────────────────┘
```

- **Local-first/CRDT:** Jeder Board-Inhalt ist ein **Yjs-Dokument**. Gleichzeitige
  Bearbeitungen werden konfliktfrei zusammengeführt (/F600/, /F650/). Der
  Sync-Server persistiert binäre Snapshots (Quelle der Wahrheit für den Canvas,
  Pflichtenheft Kap. 6.3).
- **Relationale Metadaten** (Nutzer, Boards, Freigaben, Aktivitäten) liegen
  getrennt für Autorisierung, Suche und Backup.
- **Permissive Lizenzen:** Nur MIT/BSD/Apache-2.0 im Auslieferungspfad
  (React, Yjs, Express, ws — /R100/). Kein AGPL/SSPL.

### Tech-Stack (MVP)

| Baustein | MVP | Pflichtenheft-Zielstack (Ausbau) |
|----------|-----|----------------------------------|
| Frontend | React + TypeScript + Vite | identisch (+ TipTap für Rich-Text) |
| CRDT/Sync | Yjs + y-websocket / y-protocols | identisch (+ Hocuspocus) |
| Backend | Express | NestJS |
| Persistenz | JSON + Yjs-Snapshot-Dateien | PostgreSQL + S3-Objektspeicher |
| Auth | E-Mail/Passwort + JWT (bcrypt) | + Keycloak (OIDC/SAML, 2FA) |
| Suche | In-Memory-Volltext | PostgreSQL-FTS / Meilisearch |
| Cache/PubSub | (in-process) | Valkey |

---

## Lokal starten (Entwicklung)

Voraussetzung: **Node ≥ 20** und **pnpm**.

```bash
cd visual-canvas-tool
pnpm install
cp .env.example .env          # Werte bei Bedarf anpassen

# Server (API + Sync) auf :4000 und Web-Client auf :5173 parallel:
pnpm dev
```

Dann <http://localhost:5173> öffnen, registrieren und ein Board anlegen.
Für Echtzeit-Test dasselbe Board in zwei Browserfenstern öffnen.

Einzeln:
```bash
pnpm dev:server   # nur API + Sync
pnpm dev:web      # nur Web-Client
```

## Self-Hosting (Produktion, /WK90/, /T130/)

```bash
cd visual-canvas-tool
JWT_SECRET="$(openssl rand -hex 32)" docker compose up -d --build
# Web:    http://localhost:8080
# Server: http://localhost:4000
```

Für eine öffentliche Domain `PUBLIC_API_URL`/`PUBLIC_WS_URL` und `CORS_ORIGIN`
auf die Zieldomain setzen (siehe `.env.example`). Daten liegen im Volume
`vct-data` (EU-Datenhaltung beim selbst gewählten Hoster).

---

## Bedienung (Kurz)

- **Karte hinzufügen:** linke Palette anklicken.
- **Verschieben:** Karten-Kopfzeile ziehen. **Pan:** leeren Canvas ziehen.
  **Zoom:** Mausrad oder Zoom-Steuerung unten rechts.
- **Verbinden:** „↳" auf einer Karte gedrückt halten und auf eine andere ziehen;
  Verbindung per Doppelklick löschen.
- **Teilen:** „Teilen" (nur Eigentümer) → per E-Mail einladen oder öffentlichen
  Lese-Link erzeugen.
- **Suche:** Suchfeld im Dashboard durchsucht Titel und Canvas-Inhalte.
- **Export/Löschung:** „Export" je Board; „Konto löschen" im Dashboard (DSGVO).

---

## Projektstruktur

```
visual-canvas-tool/
├── apps/
│   ├── server/            # Express-API + Yjs-WebSocket-Sync
│   │   └── src/
│   │       ├── index.ts   # Bootstrap (HTTP + WS auf einem Port)
│   │       ├── store.ts    # Persistenz (JSON + Yjs-Snapshots)
│   │       ├── auth.ts     # JWT, Passwort-Hashing, Rollen/Rechte
│   │       ├── routes.ts   # REST-Endpunkte (/F1xx–/F9xx)
│   │       └── sync.ts     # Yjs-Sync- & Awareness-Protokoll
│   └── web/                # React-SPA
│       └── src/
│           ├── App.tsx, api.ts, yboard.ts, boardOps.ts
│           └── components/ # Canvas, Card, Palette, ShareDialog, …
├── docker-compose.yml      # Self-Hosting-Paket
└── .env.example
```

---

## DSGVO-/Sicherheitsmaßnahmen (Auszug)

- EU-/Self-Hosting, keine Drittlanddienste; Link-Vorschau über **serverseitigen
  Proxy** (kein IP-Leak des Nutzers, /R90/, /F320/).
- Passwörter mit **bcrypt** gehasht; Sessions via JWT; serverseitige
  Autorisierung pro Board-Operation, Least-Privilege (/R60/).
- **Soft-Delete/Papierkorb** mit Wiederherstellung (/R80/), Audit-Log (/R70/),
  **Datenexport** und **Konto-Löschung** (/R40/).
- Nur essenzielle Daten; keine Tracking-Cookies.

## Bekannte MVP-Grenzen (Ausbaupfad)

- Bilder werden im MVP als Data-URL im Dokument gehalten (Limit 3 MB) — produktiv
  über S3-Objektspeicher mit presigned URLs (/L50/).
- Suche/Persistenz in-process — produktiv PostgreSQL + Meilisearch.
- Notiz-Rich-Text als Markdown-Textfeld — produktiv TipTap mit kollaborativem
  `Y.XmlFragment`.
- E-Mail-Versand (Verifikation/Einladung), PDF-Export (Playwright-Worker),
  Web-Clipper und SSO sind im Pflichtenheft als spätere Stufen vorgesehen.

## Lizenz

MIT — alle Laufzeitabhängigkeiten sind permissiv lizenziert (/R100/).
