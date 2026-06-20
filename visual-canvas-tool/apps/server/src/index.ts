/**
 * Bootstrap: HTTP-API (Express) + Echtzeit-Sync (WebSocket/Yjs) auf einem Port.
 */
import http from 'node:http';
import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';
import { loadDB } from './store.js';
import { api } from './routes.js';
import { attachSync } from './sync.js';

const PORT = Number(process.env.PORT || 4000);
const CORS_ORIGIN = process.env.CORS_ORIGIN || '*';

loadDB();

const app = express();
app.use(cors({ origin: CORS_ORIGIN === '*' ? true : CORS_ORIGIN.split(',') }));
app.use(express.json({ limit: '2mb' }));

app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'vct-server' }));
app.use('/api', api);

const server = http.createServer(app);
const wss = new WebSocketServer({ noServer: true });
attachSync(wss, server);

server.listen(PORT, () => {
  console.log(`[VCT] API + Sync laeuft auf http://localhost:${PORT}`);
  console.log(`[VCT] WebSocket-Sync unter ws://localhost:${PORT}/sync/<boardId>`);
});
