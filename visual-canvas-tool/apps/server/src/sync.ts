/**
 * Echtzeit-Sync-Server (/F600/, /F650/, /MK40/).
 *
 * Implementiert das Yjs-Sync- und Awareness-Protokoll ueber WebSocket. Jede
 * Board-ID entspricht genau einem geteilten Y.Doc. CRDT garantiert die
 * konfliktfreie Zusammenfuehrung gleichzeitiger Bearbeitungen; der Snapshot wird
 * debounced in der Persistenzschicht gesichert (Quelle der Wahrheit fuer den
 * Canvas, Pflichtenheft Kap. 6.3).
 */
import type { IncomingMessage } from 'node:http';
import type { Duplex } from 'node:stream';
import { WebSocketServer, WebSocket } from 'ws';
import * as Y from 'yjs';
import * as encoding from 'lib0/encoding';
import * as decoding from 'lib0/decoding';
import * as syncProtocol from 'y-protocols/sync';
import * as awarenessProtocol from 'y-protocols/awareness';
import jwt from 'jsonwebtoken';
import { store, type Role } from './store.js';
import { effectiveRole, canEdit } from './auth.js';

const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';

const MESSAGE_SYNC = 0;
const MESSAGE_AWARENESS = 1;

interface Room {
  doc: Y.Doc;
  awareness: awarenessProtocol.Awareness;
  conns: Map<WebSocket, Set<number>>;
  saveTimer: NodeJS.Timeout | null;
  dirty: boolean;
}

const rooms = new Map<string, Room>();

function getRoom(boardId: string): Room {
  let room = rooms.get(boardId);
  if (room) return room;

  const doc = new Y.Doc();
  const snapshot = store.readSnapshot(boardId);
  if (snapshot) Y.applyUpdate(doc, snapshot);

  const awareness = new awarenessProtocol.Awareness(doc);
  awareness.setLocalState(null);

  room = { doc, awareness, conns: new Map(), saveTimer: null, dirty: false };

  doc.on('update', () => {
    room!.dirty = true;
    if (room!.saveTimer) return;
    room!.saveTimer = setTimeout(() => {
      room!.saveTimer = null;
      if (room!.dirty) {
        store.writeSnapshot(boardId, Y.encodeStateAsUpdate(room!.doc));
        room!.dirty = false;
      }
    }, 800);
  });

  awareness.on(
    'update',
    ({ added, updated, removed }: { added: number[]; updated: number[]; removed: number[] }) => {
      const changed = added.concat(updated, removed);
      const enc = encoding.createEncoder();
      encoding.writeVarUint(enc, MESSAGE_AWARENESS);
      encoding.writeVarUint8Array(
        enc,
        awarenessProtocol.encodeAwarenessUpdate(awareness, changed),
      );
      broadcast(room!, encoding.toUint8Array(enc));
    },
  );

  rooms.set(boardId, room);
  return room;
}

function broadcast(room: Room, message: Uint8Array, except?: WebSocket) {
  room.conns.forEach((_ids, conn) => {
    if (conn !== except && conn.readyState === WebSocket.OPEN) {
      conn.send(message);
    }
  });
}

function closeConn(room: Room, boardId: string, conn: WebSocket) {
  const controlledIds = room.conns.get(conn);
  if (controlledIds) {
    awarenessProtocol.removeAwarenessStates(room.awareness, [...controlledIds], null);
  }
  room.conns.delete(conn);
  // Persistiere ausstehende Aenderungen und raeume leere Raeume auf.
  if (room.conns.size === 0) {
    if (room.dirty) store.writeSnapshot(boardId, Y.encodeStateAsUpdate(room.doc));
    if (room.saveTimer) clearTimeout(room.saveTimer);
    rooms.delete(boardId);
  }
}

/** Liefert Board-ID + Schreibrecht anhand von URL-Pfad und Token/Share. */
function authorize(req: IncomingMessage): { boardId: string; canWrite: boolean } | null {
  const url = new URL(req.url || '', 'http://localhost');
  const boardId = url.pathname.split('/').filter(Boolean).pop();
  if (!boardId) return null;

  const board = store.getBoard(boardId);
  if (!board || board.deletedAt) return null;

  // Oeffentlicher Lese-Link (/F640/): read-only Zugriff ohne Login.
  const publicToken = url.searchParams.get('share');
  if (publicToken) {
    const share = store.findShareByToken(publicToken);
    if (share && share.boardId === boardId) return { boardId, canWrite: false };
  }

  const token = url.searchParams.get('token');
  if (token) {
    try {
      const { sub } = jwt.verify(token, JWT_SECRET) as { sub: string };
      const role: Role | null = effectiveRole(board, sub);
      if (role) return { boardId, canWrite: canEdit(role) };
    } catch {
      /* faellt durch */
    }
  }
  return null;
}

export function attachSync(wss: WebSocketServer, server: import('node:http').Server) {
  server.on('upgrade', (req: IncomingMessage, socket: Duplex, head: Buffer) => {
    if (!req.url?.startsWith('/sync/')) return;
    const auth = authorize(req);
    if (!auth) {
      socket.write('HTTP/1.1 403 Forbidden\r\n\r\n');
      socket.destroy();
      return;
    }
    wss.handleUpgrade(req, socket, head, (ws) => {
      wss.emit('connection', ws, req, auth);
    });
  });

  wss.on(
    'connection',
    (ws: WebSocket, _req: IncomingMessage, auth: { boardId: string; canWrite: boolean }) => {
      const room = getRoom(auth.boardId);
      room.conns.set(ws, new Set());
      ws.binaryType = 'arraybuffer';

      // Initialer Sync-Step 1 (Server fragt Client-State an).
      const enc = encoding.createEncoder();
      encoding.writeVarUint(enc, MESSAGE_SYNC);
      syncProtocol.writeSyncStep1(enc, room.doc);
      ws.send(encoding.toUint8Array(enc));

      // Aktuelle Awareness-States an den neuen Client schicken.
      const states = room.awareness.getStates();
      if (states.size > 0) {
        const aenc = encoding.createEncoder();
        encoding.writeVarUint(aenc, MESSAGE_AWARENESS);
        encoding.writeVarUint8Array(
          aenc,
          awarenessProtocol.encodeAwarenessUpdate(room.awareness, [...states.keys()]),
        );
        ws.send(encoding.toUint8Array(aenc));
      }

      ws.on('message', (data: ArrayBuffer) => {
        try {
          const message = new Uint8Array(data);
          const decoder = decoding.createDecoder(message);
          const messageType = decoding.readVarUint(decoder);

          if (messageType === MESSAGE_SYNC) {
            const encoder = encoding.createEncoder();
            encoding.writeVarUint(encoder, MESSAGE_SYNC);
            const syncType = decoding.readVarUint(decoder);
            decoder.pos--; // Sync-Subtyp zurueckspulen fuer readSyncMessage

            if (!auth.canWrite && syncType === syncProtocol.messageYjsUpdate) {
              return; // Schreibversuch eines read-only-Clients verwerfen.
            }

            syncProtocol.readSyncMessage(decoder, encoder, room.doc, ws);
            if (encoding.length(encoder) > 1) ws.send(encoding.toUint8Array(encoder));

            // Update an alle anderen Clients weiterreichen.
            if (syncType === syncProtocol.messageYjsUpdate && auth.canWrite) {
              broadcast(room, message, ws);
            }
          } else if (messageType === MESSAGE_AWARENESS) {
            awarenessProtocol.applyAwarenessUpdate(
              room.awareness,
              decoding.readVarUint8Array(decoder),
              ws,
            );
          }
        } catch (err) {
          console.error('Sync-Nachricht fehlerhaft:', err);
        }
      });

      ws.on('close', () => closeConn(room, auth.boardId, ws));
      ws.on('error', () => closeConn(room, auth.boardId, ws));
    },
  );
}

/** Liest den Canvas-Text eines Boards aus dem Snapshot fuer die Volltextsuche (/F900/). */
export function extractBoardText(boardId: string): string {
  const room = rooms.get(boardId);
  const doc = new Y.Doc();
  if (room) {
    Y.applyUpdate(doc, Y.encodeStateAsUpdate(room.doc));
  } else {
    const snap = store.readSnapshot(boardId);
    if (snap) Y.applyUpdate(doc, snap);
  }
  const elements = doc.getMap('elements');
  const parts: string[] = [];
  elements.forEach((value: unknown) => {
    const el = value as Record<string, unknown>;
    if (typeof el?.text === 'string') parts.push(el.text);
    if (typeof el?.title === 'string') parts.push(el.title);
    if (typeof el?.url === 'string') parts.push(el.url);
    if (Array.isArray(el?.items)) {
      for (const it of el.items as Array<Record<string, unknown>>) {
        if (typeof it?.text === 'string') parts.push(it.text);
      }
    }
  });
  return parts.join(' \n ');
}
