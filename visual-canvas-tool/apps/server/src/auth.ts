/**
 * Authentifizierung & Rechte (/F100/–/F120/, /R60/).
 * E-Mail/Passwort mit bcrypt-Hashing und JWT-Sessions. Serverseitige
 * Autorisierung pro Board-Operation (Least-Privilege).
 */
import type { NextFunction, Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { store, type Board, type Role } from './store.js';

const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';
const TOKEN_TTL = '7d';

export interface AuthedRequest extends Request {
  userId?: string;
}

export function hashPassword(pw: string): string {
  return bcrypt.hashSync(pw, 10);
}
export function verifyPassword(pw: string, hash: string): boolean {
  return bcrypt.compareSync(pw, hash);
}
export function signToken(userId: string): string {
  return jwt.sign({ sub: userId }, JWT_SECRET, { expiresIn: TOKEN_TTL });
}

/** Erzwingt eine gueltige Session. */
export function requireAuth(req: AuthedRequest, res: Response, next: NextFunction) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Nicht authentifiziert' });
  }
  try {
    const payload = jwt.verify(header.slice(7), JWT_SECRET) as { sub: string };
    req.userId = payload.sub;
    next();
  } catch {
    res.status(401).json({ error: 'Ungueltiges Token' });
  }
}

/**
 * Ermittelt die effektive Rolle eines Nutzers fuer ein Board.
 * Eigentuemer > explizite Freigabe. Vererbung an Sub-Boards ueber die Hierarchie.
 */
export function effectiveRole(board: Board, userId: string): Role | null {
  if (board.ownerId === userId) return 'owner';
  const user = store.findUserById(userId);
  if (!user) return null;

  // Hierarchische Rechtevererbung: Freigabe auf einem Eltern-Board wirkt nach unten.
  let current: Board | undefined = board;
  const guard = new Set<string>();
  while (current && !guard.has(current.id)) {
    guard.add(current.id);
    if (current.ownerId === userId) return 'owner';
    const share = store.findShareForUser(current.id, user.email);
    if (share) return share.role;
    current = current.parentId ? store.getBoard(current.parentId) : undefined;
  }
  return null;
}

export function canEdit(role: Role | null): boolean {
  return role === 'owner' || role === 'editor';
}
