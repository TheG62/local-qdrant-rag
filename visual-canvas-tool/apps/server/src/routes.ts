/**
 * REST-API (Konten, Boards, Freigaben, Suche, Export, Link-Vorschau).
 * Bildet die Produktfunktionen /F1xx/–/F9xx/ des Lastenhefts ab.
 */
import { Router, type Response } from 'express';
import { v4 as uuid } from 'uuid';
import {
  store,
  type Board,
  type Share,
  type Role,
} from './store.js';
import {
  requireAuth,
  type AuthedRequest,
  hashPassword,
  verifyPassword,
  signToken,
  effectiveRole,
  canEdit,
} from './auth.js';
import { extractBoardText } from './sync.js';

export const api = Router();

function now() {
  return new Date().toISOString();
}

function logActivity(actorId: string, action: string, target: string) {
  store.addActivity({ id: uuid(), actorId, action, target, timestamp: now() });
}

function publicUser(id: string) {
  const u = store.findUserById(id);
  return u ? { id: u.id, name: u.name, email: u.email, locale: u.locale } : null;
}

// ---------------------------------------------------------------------------
// Konten & Auth (/F100/, /F110/)
// ---------------------------------------------------------------------------
api.post('/auth/register', (req, res) => {
  const { name, email, password } = req.body ?? {};
  if (!name || !email || !password) {
    return res.status(400).json({ error: 'name, email und password sind erforderlich' });
  }
  if (String(password).length < 8) {
    return res.status(400).json({ error: 'Passwort muss mind. 8 Zeichen haben' });
  }
  if (store.findUserByEmail(email)) {
    return res.status(409).json({ error: 'E-Mail bereits registriert' });
  }
  const user = store.addUser({
    id: uuid(),
    name,
    email,
    passwordHash: hashPassword(password),
    locale: 'de',
    createdAt: now(),
  });

  // Home-Board automatisch anlegen (/F210/, /MK30/).
  const home: Board = {
    id: uuid(),
    title: 'Mein Home-Board',
    parentId: null,
    ownerId: user.id,
    workspaceId: user.id,
    isHome: true,
    createdAt: now(),
    updatedAt: now(),
    deletedAt: null,
  };
  store.addBoard(home);
  logActivity(user.id, 'register', user.id);

  res.status(201).json({ token: signToken(user.id), user: publicUser(user.id) });
});

api.post('/auth/login', (req, res) => {
  const { email, password } = req.body ?? {};
  const user = email ? store.findUserByEmail(email) : undefined;
  if (!user || !verifyPassword(String(password ?? ''), user.passwordHash)) {
    return res.status(401).json({ error: 'E-Mail oder Passwort ungueltig' });
  }
  logActivity(user.id, 'login', user.id);
  res.json({ token: signToken(user.id), user: publicUser(user.id) });
});

api.get('/me', requireAuth, (req: AuthedRequest, res) => {
  res.json({ user: publicUser(req.userId!) });
});

// Konto-Loeschung / Recht auf Vergessenwerden (/R40/)
api.delete('/me', requireAuth, (req: AuthedRequest, res) => {
  const userId = req.userId!;
  const db = store.raw();
  db.boards = db.boards.filter((b) => b.ownerId !== userId);
  db.shares = db.shares.filter((s) => {
    const u = store.findUserById(userId);
    return s.email?.toLowerCase() !== u?.email.toLowerCase();
  });
  db.users = db.users.filter((u) => u.id !== userId);
  logActivity(userId, 'account_deleted', userId);
  res.json({ ok: true });
});

// ---------------------------------------------------------------------------
// Board-Verwaltung (/F200/–/F230/)
// ---------------------------------------------------------------------------
api.get('/boards', requireAuth, (req: AuthedRequest, res) => {
  const boards = store.listBoards(req.userId!).map((b) => ({
    ...b,
    role: effectiveRole(b, req.userId!),
  }));
  res.json({ boards });
});

api.get('/boards/trash', requireAuth, (req: AuthedRequest, res) => {
  res.json({ boards: store.listTrash(req.userId!) });
});

api.post('/boards', requireAuth, (req: AuthedRequest, res) => {
  const { title, parentId } = req.body ?? {};
  if (parentId) {
    const parent = store.getBoard(parentId);
    if (!parent || !canEdit(effectiveRole(parent, req.userId!))) {
      return res.status(403).json({ error: 'Kein Schreibrecht am Eltern-Board' });
    }
  }
  const board: Board = {
    id: uuid(),
    title: title?.trim() || 'Neues Board',
    parentId: parentId || null,
    ownerId: req.userId!,
    workspaceId: req.userId!,
    isHome: false,
    createdAt: now(),
    updatedAt: now(),
    deletedAt: null,
  };
  store.addBoard(board);
  logActivity(req.userId!, 'board_created', board.id);
  res.status(201).json({ board });
});

/** Laedt ein Board (Metadaten + effektive Rolle). */
api.get('/boards/:id', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board || board.deletedAt) return res.status(404).json({ error: 'Nicht gefunden' });
  const role = effectiveRole(board, req.userId!);
  if (!role) return res.status(403).json({ error: 'Kein Zugriff' });
  const children = store
    .listBoards(board.ownerId)
    .filter((b) => b.parentId === board.id);
  res.json({ board: { ...board, role }, children });
});

api.patch('/boards/:id', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board || board.deletedAt) return res.status(404).json({ error: 'Nicht gefunden' });
  if (!canEdit(effectiveRole(board, req.userId!))) {
    return res.status(403).json({ error: 'Kein Schreibrecht' });
  }
  const { title, parentId } = req.body ?? {};
  const patch: Partial<Board> = {};
  if (typeof title === 'string') patch.title = title.trim() || board.title;
  if (parentId !== undefined) patch.parentId = parentId || null;
  const updated = store.updateBoard(board.id, patch);
  logActivity(req.userId!, 'board_updated', board.id);
  res.json({ board: updated });
});

/** Board duplizieren (/F200/) — inkl. Canvas-Snapshot. */
api.post('/boards/:id/duplicate', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board || board.deletedAt) return res.status(404).json({ error: 'Nicht gefunden' });
  if (!effectiveRole(board, req.userId!)) return res.status(403).json({ error: 'Kein Zugriff' });
  const copy: Board = {
    ...board,
    id: uuid(),
    title: `${board.title} (Kopie)`,
    ownerId: req.userId!,
    isHome: false,
    createdAt: now(),
    updatedAt: now(),
  };
  store.addBoard(copy);
  const snap = store.readSnapshot(board.id);
  if (snap) store.writeSnapshot(copy.id, snap);
  logActivity(req.userId!, 'board_duplicated', copy.id);
  res.status(201).json({ board: copy });
});

/** Soft-Delete in Papierkorb (/R80/, /D90/). */
api.delete('/boards/:id', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board) return res.status(404).json({ error: 'Nicht gefunden' });
  if (board.ownerId !== req.userId!) return res.status(403).json({ error: 'Nur Eigentuemer' });
  store.updateBoard(board.id, { deletedAt: now() });
  logActivity(req.userId!, 'board_trashed', board.id);
  res.json({ ok: true });
});

api.post('/boards/:id/restore', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board) return res.status(404).json({ error: 'Nicht gefunden' });
  if (board.ownerId !== req.userId!) return res.status(403).json({ error: 'Nur Eigentuemer' });
  store.updateBoard(board.id, { deletedAt: null });
  res.json({ board });
});

// ---------------------------------------------------------------------------
// Freigaben & oeffentliche Links (/F630/, /F640/, /MK50/)
// ---------------------------------------------------------------------------
api.get('/boards/:id/shares', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board) return res.status(404).json({ error: 'Nicht gefunden' });
  if (board.ownerId !== req.userId!) return res.status(403).json({ error: 'Nur Eigentuemer' });
  res.json({ shares: store.listShares(board.id) });
});

api.post('/boards/:id/shares', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board) return res.status(404).json({ error: 'Nicht gefunden' });
  if (board.ownerId !== req.userId!) return res.status(403).json({ error: 'Nur Eigentuemer' });

  const { email, role, publicLink } = req.body ?? {};
  if (publicLink) {
    const existing = store.listShares(board.id).find((s) => s.publicToken);
    if (existing) return res.json({ share: existing });
    const share: Share = {
      id: uuid(),
      boardId: board.id,
      email: null,
      role: 'viewer',
      publicToken: uuid().replace(/-/g, ''),
      createdAt: now(),
    };
    store.addShare(share);
    logActivity(req.userId!, 'public_link_created', board.id);
    return res.status(201).json({ share });
  }

  const validRoles: Role[] = ['editor', 'viewer'];
  if (!email || !validRoles.includes(role)) {
    return res.status(400).json({ error: 'email und gueltige role (editor|viewer) erforderlich' });
  }
  const share: Share = {
    id: uuid(),
    boardId: board.id,
    email: String(email).toLowerCase(),
    role,
    publicToken: null,
    createdAt: now(),
  };
  store.addShare(share);
  logActivity(req.userId!, 'board_shared', board.id);
  res.status(201).json({ share });
});

api.delete('/shares/:id', requireAuth, (req: AuthedRequest, res) => {
  store.removeShare(req.params.id);
  res.json({ ok: true });
});

/** Oeffentlicher, schreibgeschuetzter Zugriff per Token (/F640/) — ohne Login. */
api.get('/public/:token', (req, res) => {
  const share = store.findShareByToken(req.params.token);
  if (!share) return res.status(404).json({ error: 'Link ungueltig' });
  const board = store.getBoard(share.boardId);
  if (!board || board.deletedAt) return res.status(404).json({ error: 'Board nicht verfuegbar' });
  res.json({ board: { id: board.id, title: board.title }, token: req.params.token });
});

// ---------------------------------------------------------------------------
// Volltextsuche (/F900/, /MK60/)
// ---------------------------------------------------------------------------
api.get('/search', requireAuth, (req: AuthedRequest, res) => {
  const q = String(req.query.q ?? '').trim().toLowerCase();
  if (!q) return res.json({ results: [] });
  const results = store
    .listBoards(req.userId!)
    .map((b) => {
      const haystack = `${b.title}\n${extractBoardText(b.id)}`.toLowerCase();
      const idx = haystack.indexOf(q);
      if (idx === -1) return null;
      const snippet = haystack.slice(Math.max(0, idx - 30), idx + 60).replace(/\s+/g, ' ');
      return { boardId: b.id, title: b.title, snippet };
    })
    .filter(Boolean);
  res.json({ results });
});

// ---------------------------------------------------------------------------
// Aktivitaetsprotokoll (/F430/, /R70/)
// ---------------------------------------------------------------------------
api.get('/boards/:id/activity', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board || !effectiveRole(board, req.userId!)) {
    return res.status(403).json({ error: 'Kein Zugriff' });
  }
  const activities = store.listActivities(board.id).map((a) => ({
    ...a,
    actor: publicUser(a.actorId)?.name ?? 'Unbekannt',
  }));
  res.json({ activities });
});

// ---------------------------------------------------------------------------
// Datenexport / Portabilitaet (/F830/, /R40/)
// ---------------------------------------------------------------------------
api.get('/boards/:id/export', requireAuth, (req: AuthedRequest, res) => {
  const board = store.getBoard(req.params.id);
  if (!board || !effectiveRole(board, req.userId!)) {
    return res.status(403).json({ error: 'Kein Zugriff' });
  }
  res.json({
    board,
    canvasText: extractBoardText(board.id),
    exportedAt: now(),
    format: 'vct-board-export-v1',
  });
});

// ---------------------------------------------------------------------------
// Link-Vorschau ueber serverseitigen Proxy (/F320/, /R90/ — kein IP-Leak)
// ---------------------------------------------------------------------------
api.get('/link-preview', requireAuth, async (req: AuthedRequest, res: Response) => {
  const target = String(req.query.url ?? '');
  if (!/^https?:\/\//i.test(target)) {
    return res.status(400).json({ error: 'Gueltige URL erforderlich' });
  }
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 6000);
    const resp = await fetch(target, {
      signal: ctrl.signal,
      headers: { 'user-agent': 'VisualCanvasTool-LinkPreview/1.0' },
    });
    clearTimeout(t);
    const html = (await resp.text()).slice(0, 200_000);
    const meta = (prop: string) => {
      const re = new RegExp(
        `<meta[^>]+(?:property|name)=["']${prop}["'][^>]+content=["']([^"']+)["']`,
        'i',
      );
      return re.exec(html)?.[1];
    };
    const titleTag = /<title[^>]*>([^<]+)<\/title>/i.exec(html)?.[1];
    res.json({
      url: target,
      title: meta('og:title') || titleTag || target,
      description: meta('og:description') || meta('description') || '',
      image: meta('og:image') || '',
      siteName: meta('og:site_name') || new URL(target).hostname,
    });
  } catch {
    res.json({ url: target, title: target, description: '', image: '', siteName: '' });
  }
});
