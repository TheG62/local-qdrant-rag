import { useState } from 'react';
import type { YBoard } from '../yboard';
import type { Comment } from '../types';
import { v4 as uuid } from '../uuid';

/** Inline-/Board-Kommentare (/F610/, /MK40/) — in Echtzeit via Yjs. */
export function CommentsPanel({
  yboard,
  comments,
  authorName,
  readOnly,
  onClose,
}: {
  yboard: YBoard;
  comments: Comment[];
  authorName: string;
  readOnly: boolean;
  onClose: () => void;
}) {
  const [text, setText] = useState('');

  const post = () => {
    if (!text.trim()) return;
    yboard.comments.push([
      {
        id: uuid(),
        elementId: null,
        authorName,
        text: text.trim(),
        createdAt: new Date().toISOString(),
      },
    ]);
    setText('');
  };

  return (
    <aside className="comments-panel">
      <div className="comments-head">
        <strong>Kommentare</strong>
        <button className="mini" onClick={onClose}>
          ✕
        </button>
      </div>
      <div className="comments-list">
        {comments.length === 0 && <p className="muted">Noch keine Kommentare.</p>}
        {comments.map((c) => (
          <div key={c.id} className="comment">
            <div className="comment-meta">
              <strong>{c.authorName}</strong>
              <span className="muted small">
                {new Date(c.createdAt).toLocaleString('de-DE')}
              </span>
            </div>
            <div>{c.text}</div>
          </div>
        ))}
      </div>
      {!readOnly && (
        <form
          className="comment-form"
          onSubmit={(e) => {
            e.preventDefault();
            post();
          }}
        >
          <textarea
            placeholder="Kommentar schreiben…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <button type="submit">Senden</button>
        </form>
      )}
    </aside>
  );
}
