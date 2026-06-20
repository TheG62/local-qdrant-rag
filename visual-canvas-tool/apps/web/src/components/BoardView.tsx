import { useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../authStore';
import { navigate } from '../App';
import { useYBoard } from '../yboard';
import { makeOps } from '../boardOps';
import { Canvas } from './Canvas';
import { Palette } from './Palette';
import { ShareDialog } from './ShareDialog';
import { CommentsPanel } from './CommentsPanel';
import type { Board } from '../types';
import { getToken } from '../api';

export function BoardView({ boardId }: { boardId: string }) {
  const { user } = useAuth();
  const [board, setBoard] = useState<Board | null>(null);
  const [, setChildren] = useState<Board[]>([]);
  const [error, setError] = useState('');
  const [showShare, setShowShare] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  const { yboard, elements, connections, comments, peers, synced } = useYBoard(boardId, {
    name: user?.name || 'Gast',
    token: getToken() || undefined,
  });

  useEffect(() => {
    api
      .getBoard(boardId)
      .then(({ board, children }) => {
        setBoard(board);
        setChildren(children);
      })
      .catch((e) => setError((e as Error).message));
  }, [boardId]);

  const readOnly = board?.role === 'viewer';
  const ops = useMemo(() => (yboard ? makeOps(yboard) : null), [yboard]);

  const saveTitle = async () => {
    const t = titleRef.current?.value.trim();
    if (board && t && t !== board.title) {
      const { board: updated } = await api.updateBoard(board.id, { title: t });
      setBoard(updated);
    }
  };

  const createSubBoard = async () => {
    const title = prompt('Titel des Sub-Boards?');
    if (title === null || !ops || !board) return;
    const { board: sub } = await api.createBoard(title || 'Sub-Board', board.id);
    // Verknuepfungskarte auf dem Canvas anlegen (/F210/, /F220/).
    ops.add({
      id: sub.id,
      type: 'board-link',
      x: 120,
      y: 120,
      width: 200,
      height: 90,
      title: sub.title,
      targetBoardId: sub.id,
      z: 1,
    });
    setChildren((c) => [...c, sub]);
  };

  const exportBoard = async () => {
    const data = await api.exportBoard(boardId);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${board?.title || 'board'}.json`;
    a.click();
  };

  if (error) {
    return (
      <div className="centered">
        <p className="error">{error}</p>
        <button onClick={() => navigate('#/')}>Zur Uebersicht</button>
      </div>
    );
  }

  return (
    <div className="board-view">
      <header className="board-topbar">
        <button className="ghost" onClick={() => navigate('#/')}>
          ← Uebersicht
        </button>
        <input
          ref={titleRef}
          className="board-title-input"
          defaultValue={board?.title ?? '…'}
          onBlur={saveTitle}
          disabled={readOnly}
        />
        <span className={`sync-badge ${synced ? 'ok' : ''}`}>
          {synced ? '● synchron' : '○ verbinde…'}
        </span>
        <div className="spacer" />

        <div className="presence">
          {peers.map((p) => (
            <span
              key={p.clientId}
              className="avatar"
              title={p.name}
              style={{ background: p.color }}
            >
              {p.name.slice(0, 1).toUpperCase()}
            </span>
          ))}
        </div>

        <button className="ghost" onClick={() => setShowComments((s) => !s)}>
          💬 {comments.length}
        </button>
        <button className="ghost" onClick={exportBoard}>
          Export
        </button>
        {board?.role === 'owner' && (
          <button onClick={() => setShowShare(true)}>Teilen</button>
        )}
      </header>

      {ops && !readOnly && (
        <Palette ops={ops} onCreateSubBoard={createSubBoard} />
      )}

      <Canvas
        yboard={yboard}
        ops={ops}
        elements={elements}
        connections={connections}
        peers={peers}
        readOnly={readOnly}
      />

      {showShare && board && (
        <ShareDialog board={board} onClose={() => setShowShare(false)} />
      )}
      {showComments && yboard && (
        <CommentsPanel
          yboard={yboard}
          comments={comments}
          authorName={user?.name || 'Gast'}
          readOnly={readOnly}
          onClose={() => setShowComments(false)}
        />
      )}
    </div>
  );
}
