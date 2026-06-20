import { v4 as uuid } from '../uuid';
import type { BoardOps } from '../boardOps';
import type { CanvasElement, ElementType } from '../types';

const NOTE_COLORS = ['#fff9c4', '#ffffff', '#ffe0e0', '#e0f0ff', '#e6ffe6'];

/** Element-Palette (/B10/) — Karten per Klick einfuegen. */
export function Palette({
  ops,
  onCreateSubBoard,
}: {
  ops: BoardOps;
  onCreateSubBoard: () => void;
}) {
  const base = () => ({
    id: uuid(),
    x: 80 + Math.random() * 120,
    y: 80 + Math.random() * 120,
    z: 1,
  });

  const add = (type: ElementType) => {
    const b = base();
    const defaults: Record<string, Partial<CanvasElement>> = {
      note: { width: 220, height: 160, text: '', color: NOTE_COLORS[0] },
      link: { width: 240, height: 90, url: '', title: 'Neuer Link' },
      image: { width: 220, height: 180, src: '' },
      todo: { width: 240, height: 180, title: 'To-do', items: [] },
      column: { width: 220, height: 320, title: 'Spalte', color: '#f1f5f9' },
      swatch: { width: 90, height: 90, color: '#2563eb' },
    };
    ops.add({ ...b, type, width: 200, height: 160, ...(defaults[type] || {}) } as CanvasElement);
  };

  const items: { type: ElementType; label: string; icon: string }[] = [
    { type: 'note', label: 'Notiz', icon: '📝' },
    { type: 'link', label: 'Link', icon: '🔗' },
    { type: 'image', label: 'Bild', icon: '🖼️' },
    { type: 'todo', label: 'To-do', icon: '☑️' },
    { type: 'column', label: 'Spalte', icon: '🗄️' },
    { type: 'swatch', label: 'Farbe', icon: '🎨' },
  ];

  return (
    <aside className="palette">
      {items.map((it) => (
        <button key={it.type} className="palette-item" onClick={() => add(it.type)}>
          <span className="palette-icon">{it.icon}</span>
          {it.label}
        </button>
      ))}
      <button className="palette-item" onClick={onCreateSubBoard}>
        <span className="palette-icon">🗂️</span>
        Sub-Board
      </button>
    </aside>
  );
}
