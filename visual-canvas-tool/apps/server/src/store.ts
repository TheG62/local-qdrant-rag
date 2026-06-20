/**
 * Persistenzschicht (MVP).
 *
 * Bewusst abhaengigkeitsarm: relationale Metadaten (Nutzer, Boards, Freigaben,
 * Aktivitaeten) liegen als JSON-Datei vor, die kollaborativen Canvas-Inhalte je
 * Board als binaerer Yjs-Snapshot (Quelle der Wahrheit fuer den Canvas, vgl.
 * Pflichtenheft Kap. 6.3). In der Ausbaustufe wird dies durch PostgreSQL +
 * S3-kompatiblen Objektspeicher ersetzt; die Modul-Schnittstelle bleibt gleich.
 */
import fs from 'node:fs';
import path from 'node:path';

const DATA_DIR = process.env.DATA_DIR || './data';
const DB_FILE = path.join(DATA_DIR, 'db.json');
const BOARDS_DIR = path.join(DATA_DIR, 'boards');

export interface User {
  id: string;
  name: string;
  email: string;
  passwordHash: string;
  locale: string;
  createdAt: string;
}

export type Role = 'owner' | 'editor' | 'viewer';

export interface Board {
  id: string;
  title: string;
  parentId: string | null;
  ownerId: string;
  workspaceId: string;
  isHome: boolean;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null; // Soft-Delete / Papierkorb (/R80/, /D90/)
}

export interface Share {
  id: string;
  boardId: string;
  /** Eingeladene Person (E-Mail) — oder null bei oeffentlichem Lese-Link */
  email: string | null;
  role: Role;
  /** Token fuer oeffentlichen read-only Link (/F640/), sonst null */
  publicToken: string | null;
  createdAt: string;
}

export interface Activity {
  id: string;
  actorId: string;
  action: string;
  target: string;
  timestamp: string;
}

interface DBShape {
  users: User[];
  boards: Board[];
  shares: Share[];
  activities: Activity[];
}

const empty: DBShape = { users: [], boards: [], shares: [], activities: [] };

function ensureDirs() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.mkdirSync(BOARDS_DIR, { recursive: true });
}

let db: DBShape = empty;

export function loadDB(): void {
  ensureDirs();
  if (fs.existsSync(DB_FILE)) {
    try {
      db = { ...empty, ...JSON.parse(fs.readFileSync(DB_FILE, 'utf-8')) };
    } catch {
      db = { ...empty };
    }
  } else {
    db = { ...empty };
    persist();
  }
}

let writeTimer: NodeJS.Timeout | null = null;
function persist(): void {
  if (writeTimer) return;
  writeTimer = setTimeout(() => {
    writeTimer = null;
    fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2));
  }, 50);
}

export const store = {
  // --- Users ---
  findUserByEmail: (email: string) =>
    db.users.find((u) => u.email.toLowerCase() === email.toLowerCase()),
  findUserById: (id: string) => db.users.find((u) => u.id === id),
  addUser: (u: User) => {
    db.users.push(u);
    persist();
    return u;
  },

  // --- Boards ---
  listBoards: (userId: string) =>
    db.boards.filter((b) => !b.deletedAt && b.ownerId === userId),
  listTrash: (userId: string) =>
    db.boards.filter((b) => b.deletedAt && b.ownerId === userId),
  getBoard: (id: string) => db.boards.find((b) => b.id === id),
  addBoard: (b: Board) => {
    db.boards.push(b);
    persist();
    return b;
  },
  updateBoard: (id: string, patch: Partial<Board>) => {
    const b = db.boards.find((x) => x.id === id);
    if (!b) return undefined;
    Object.assign(b, patch, { updatedAt: new Date().toISOString() });
    persist();
    return b;
  },

  // --- Shares ---
  listShares: (boardId: string) => db.shares.filter((s) => s.boardId === boardId),
  findShareByToken: (token: string) =>
    db.shares.find((s) => s.publicToken === token),
  findShareForUser: (boardId: string, email: string) =>
    db.shares.find(
      (s) => s.boardId === boardId && s.email?.toLowerCase() === email.toLowerCase(),
    ),
  addShare: (s: Share) => {
    db.shares.push(s);
    persist();
    return s;
  },
  removeShare: (id: string) => {
    db.shares = db.shares.filter((s) => s.id !== id);
    persist();
  },

  // --- Activity (/R70/, /D80/) ---
  addActivity: (a: Activity) => {
    db.activities.push(a);
    if (db.activities.length > 5000) db.activities.splice(0, 1000);
    persist();
  },
  listActivities: (target: string) =>
    db.activities.filter((a) => a.target === target).slice(-200),

  // --- Yjs-Snapshots (binaer) ---
  snapshotPath: (boardId: string) => path.join(BOARDS_DIR, `${boardId}.ybin`),
  readSnapshot: (boardId: string): Uint8Array | null => {
    const p = path.join(BOARDS_DIR, `${boardId}.ybin`);
    return fs.existsSync(p) ? new Uint8Array(fs.readFileSync(p)) : null;
  },
  writeSnapshot: (boardId: string, data: Uint8Array) => {
    ensureDirs();
    fs.writeFileSync(path.join(BOARDS_DIR, `${boardId}.ybin`), Buffer.from(data));
  },

  raw: () => db,
};
