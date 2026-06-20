/**
 * React-Hook fuer die kollaborative Board-Bindung.
 * Stellt das Yjs-Dokument, die Element-Map, Verbindungen, Kommentare und die
 * Awareness (Presence/Cursor, /F600/) bereit und haelt React-State synchron.
 */
import { useEffect, useRef, useState } from 'react';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { WS_URL } from './api';
import type { CanvasElement, Comment, Connection } from './types';

export interface PresenceUser {
  clientId: number;
  name: string;
  color: string;
  cursor?: { x: number; y: number };
}

export interface YBoard {
  doc: Y.Doc;
  provider: WebsocketProvider;
  elements: Y.Map<CanvasElement>;
  connections: Y.Map<Connection>;
  comments: Y.Array<Comment>;
  synced: boolean;
}

const COLORS = ['#2563eb', '#dc2626', '#16a34a', '#d97706', '#7c3aed', '#0891b2', '#db2777'];

export function useYBoard(
  boardId: string,
  identity: { name: string; token?: string; shareToken?: string },
) {
  const [yboard, setYboard] = useState<YBoard | null>(null);
  const [elements, setElements] = useState<CanvasElement[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [peers, setPeers] = useState<PresenceUser[]>([]);
  const [synced, setSynced] = useState(false);
  const identityRef = useRef(identity);
  identityRef.current = identity;

  useEffect(() => {
    const doc = new Y.Doc();
    const params: Record<string, string> = {};
    if (identityRef.current.token) params.token = identityRef.current.token;
    if (identityRef.current.shareToken) params.share = identityRef.current.shareToken;

    const provider = new WebsocketProvider(`${WS_URL}/sync`, boardId, doc, { params });
    const elements = doc.getMap<CanvasElement>('elements');
    const connections = doc.getMap<Connection>('connections');
    const comments = doc.getArray<Comment>('comments');

    const color = COLORS[Math.floor(Math.random() * COLORS.length)];
    provider.awareness.setLocalStateField('user', {
      name: identityRef.current.name,
      color,
    });

    const refreshElements = () => setElements([...elements.values()]);
    const refreshConnections = () => setConnections([...connections.values()]);
    const refreshComments = () => setComments(comments.toArray());
    const refreshPeers = () => {
      const states = provider.awareness.getStates();
      const list: PresenceUser[] = [];
      states.forEach((state, clientId) => {
        if (clientId === provider.awareness.clientID) return;
        if (state.user) {
          list.push({
            clientId,
            name: state.user.name,
            color: state.user.color,
            cursor: state.cursor,
          });
        }
      });
      setPeers(list);
    };

    elements.observeDeep(refreshElements);
    connections.observeDeep(refreshConnections);
    comments.observe(refreshComments);
    provider.awareness.on('change', refreshPeers);
    provider.on('sync', (isSynced: boolean) => {
      setSynced(isSynced);
      refreshElements();
      refreshConnections();
      refreshComments();
    });

    refreshElements();
    refreshConnections();
    refreshComments();

    setYboard({ doc, provider, elements, connections, comments, synced: false });

    return () => {
      provider.awareness.off('change', refreshPeers);
      provider.destroy();
      doc.destroy();
      setYboard(null);
      setSynced(false);
    };
  }, [boardId]);

  return { yboard, elements, connections, comments, peers, synced };
}
