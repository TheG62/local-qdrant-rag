export type Role = 'owner' | 'editor' | 'viewer';

export interface User {
  id: string;
  name: string;
  email: string;
  locale: string;
}

export interface Board {
  id: string;
  title: string;
  parentId: string | null;
  ownerId: string;
  isHome: boolean;
  createdAt: string;
  updatedAt: string;
  deletedAt: string | null;
  role?: Role;
}

export interface Share {
  id: string;
  boardId: string;
  email: string | null;
  role: Role;
  publicToken: string | null;
}

export type ElementType =
  | 'note'
  | 'image'
  | 'link'
  | 'todo'
  | 'column'
  | 'board-link'
  | 'swatch';

export interface TodoItem {
  id: string;
  text: string;
  done: boolean;
}

/** Ein Canvas-Element. Lebt im Yjs-Dokument (konfliktfrei synchronisiert). */
export interface CanvasElement {
  id: string;
  type: ElementType;
  x: number;
  y: number;
  width: number;
  height: number;
  color?: string;
  labels?: string[];
  z?: number;
  // typabhaengiger Inhalt
  text?: string;
  title?: string;
  url?: string;
  preview?: { title?: string; description?: string; image?: string; siteName?: string };
  src?: string;
  items?: TodoItem[];
  targetBoardId?: string;
}

export interface Connection {
  id: string;
  source: string;
  target: string;
  label?: string;
  style?: 'straight' | 'curved';
}

export interface Comment {
  id: string;
  elementId: string | null;
  authorName: string;
  text: string;
  createdAt: string;
}
