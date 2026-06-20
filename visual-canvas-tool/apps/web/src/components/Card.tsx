import { useState } from 'react';
import { api } from '../api';
import { navigate } from '../App';
import { v4 as uuid } from '../uuid';
import type { BoardOps } from '../boardOps';
import type { CanvasElement, TodoItem } from '../types';

const NOTE_COLORS = ['#fff9c4', '#ffffff', '#ffe0e0', '#e0f0ff', '#e6ffe6', '#f1f5f9'];

export function Card({
  element: el,
  selected,
  readOnly,
  ops,
  onStartDrag,
  onStartConnect,
  onSelect,
}: {
  element: CanvasElement;
  selected: boolean;
  readOnly: boolean;
  ops: BoardOps | null;
  onStartDrag: (id: string, e: React.PointerEvent) => void;
  onStartConnect: (id: string, e: React.PointerEvent) => void;
  onSelect: (id: string) => void;
}) {
  const update = (patch: Partial<CanvasElement>) => ops?.update(el.id, patch);
  const stop = (e: React.PointerEvent) => e.stopPropagation();

  return (
    <div
      className={`card card-${el.type} ${selected ? 'selected' : ''}`}
      style={{
        left: el.x,
        top: el.y,
        width: el.width,
        height: el.type === 'swatch' ? el.width : el.height,
        background: el.color,
        zIndex: el.z || 0,
      }}
      onPointerDown={() => onSelect(el.id)}
    >
      {!readOnly && (
        <div
          className="card-header"
          onPointerDown={(e) => {
            e.stopPropagation();
            onStartDrag(el.id, e);
          }}
        >
          <span className="card-type-label">{labelFor(el.type)}</span>
          <div className="card-tools">
            <button
              title="Verbinden"
              className="mini"
              onPointerDown={(e) => {
                e.stopPropagation();
                onStartConnect(el.id, e);
              }}
            >
              ↳
            </button>
            <button
              title="Loeschen"
              className="mini"
              onPointerDown={stop}
              onClick={() => ops?.remove(el.id)}
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <div className="card-body" onPointerDown={stop}>
        <CardContent el={el} readOnly={readOnly} update={update} />
      </div>

      {selected && !readOnly && ['note', 'column', 'swatch'].includes(el.type) && (
        <div className="color-row" onPointerDown={stop}>
          {NOTE_COLORS.map((c) => (
            <span
              key={c}
              className="color-dot"
              style={{ background: c }}
              onClick={() => update({ color: c })}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function labelFor(t: string) {
  return (
    {
      note: 'Notiz',
      link: 'Link',
      image: 'Bild',
      todo: 'To-do',
      column: 'Spalte',
      swatch: 'Farbe',
      'board-link': 'Board',
    } as Record<string, string>
  )[t] || t;
}

function CardContent({
  el,
  readOnly,
  update,
}: {
  el: CanvasElement;
  readOnly: boolean;
  update: (patch: Partial<CanvasElement>) => void;
}) {
  switch (el.type) {
    case 'note':
      return (
        <textarea
          className="note-text"
          placeholder="Notiz schreiben… (Markdown moeglich)"
          value={el.text || ''}
          readOnly={readOnly}
          onChange={(e) => update({ text: e.target.value })}
        />
      );

    case 'image':
      return <ImageCard el={el} readOnly={readOnly} update={update} />;

    case 'link':
      return <LinkCard el={el} readOnly={readOnly} update={update} />;

    case 'todo':
      return <TodoCard el={el} readOnly={readOnly} update={update} />;

    case 'column':
      return (
        <input
          className="column-title"
          value={el.title || ''}
          readOnly={readOnly}
          placeholder="Spaltentitel"
          onChange={(e) => update({ title: e.target.value })}
        />
      );

    case 'swatch':
      return (
        <div className="swatch-hex" title="Farbwert">
          {el.color}
        </div>
      );

    case 'board-link':
      return (
        <div
          className="board-link"
          onDoubleClick={() => el.targetBoardId && navigate(`#/board/${el.targetBoardId}`)}
        >
          🗂️ {el.title || 'Board'}
          <div className="muted small">Doppelklick zum Oeffnen</div>
        </div>
      );

    default:
      return null;
  }
}

function ImageCard({
  el,
  readOnly,
  update,
}: {
  el: CanvasElement;
  readOnly: boolean;
  update: (patch: Partial<CanvasElement>) => void;
}) {
  if (el.src) {
    return <img className="image-card-img" src={el.src} alt={el.title || 'Bild'} />;
  }
  if (readOnly) return <div className="muted">Kein Bild</div>;
  return (
    <label className="image-drop">
      Bild waehlen
      <input
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          if (file.size > 3_000_000) {
            alert('Bild zu gross (MVP-Limit 3 MB; produktiv via Objektspeicher).');
            return;
          }
          const reader = new FileReader();
          reader.onload = () => update({ src: reader.result as string });
          reader.readAsDataURL(file);
        }}
      />
    </label>
  );
}

function LinkCard({
  el,
  readOnly,
  update,
}: {
  el: CanvasElement;
  readOnly: boolean;
  update: (patch: Partial<CanvasElement>) => void;
}) {
  const [draft, setDraft] = useState(el.url || '');
  const [loading, setLoading] = useState(false);

  if (el.preview?.title || (el.url && readOnly)) {
    return (
      <a className="link-preview" href={el.url} target="_blank" rel="noreferrer">
        {el.preview?.image && <img src={el.preview.image} alt="" />}
        <div className="link-preview-text">
          <strong>{el.preview?.title || el.url}</strong>
          <span className="muted small">{el.preview?.siteName}</span>
          <p className="muted small">{el.preview?.description}</p>
        </div>
      </a>
    );
  }
  if (readOnly) return <div className="muted">Kein Link</div>;

  return (
    <div className="link-input">
      <input
        placeholder="https://…"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <button
        disabled={loading || !draft}
        onClick={async () => {
          setLoading(true);
          try {
            const preview = await api.linkPreview(draft);
            update({ url: draft, preview });
          } catch {
            update({ url: draft, title: draft });
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? '…' : 'Vorschau'}
      </button>
    </div>
  );
}

function TodoCard({
  el,
  readOnly,
  update,
}: {
  el: CanvasElement;
  readOnly: boolean;
  update: (patch: Partial<CanvasElement>) => void;
}) {
  const items = el.items || [];
  const [draft, setDraft] = useState('');

  const setItems = (next: TodoItem[]) => update({ items: next });

  return (
    <div className="todo-card">
      <input
        className="todo-title"
        value={el.title || ''}
        readOnly={readOnly}
        onChange={(e) => update({ title: e.target.value })}
        placeholder="Titel"
      />
      <ul className="todo-list">
        {items.map((it) => (
          <li key={it.id}>
            <input
              type="checkbox"
              checked={it.done}
              disabled={readOnly}
              onChange={() =>
                setItems(items.map((x) => (x.id === it.id ? { ...x, done: !x.done } : x)))
              }
            />
            <span className={it.done ? 'done' : ''}>{it.text}</span>
            {!readOnly && (
              <button
                className="mini"
                onClick={() => setItems(items.filter((x) => x.id !== it.id))}
              >
                ✕
              </button>
            )}
          </li>
        ))}
      </ul>
      {!readOnly && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (!draft.trim()) return;
            setItems([...items, { id: uuid(), text: draft.trim(), done: false }]);
            setDraft('');
          }}
        >
          <input
            placeholder="+ Aufgabe"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </form>
      )}
    </div>
  );
}
