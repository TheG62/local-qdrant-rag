import { useEffect, useState } from 'react';
import { api } from '../api';
import { useYBoard } from '../yboard';
import { Canvas } from './Canvas';

/** Oeffentlicher, schreibgeschuetzter Board-Zugriff ohne Login (/F640/, /TS30/). */
export function PublicBoardView({ token }: { token: string }) {
  const [boardId, setBoardId] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .publicBoard(token)
      .then(({ board }) => {
        setBoardId(board.id);
        setTitle(board.title);
      })
      .catch((e) => setError((e as Error).message));
  }, [token]);

  if (error) return <div className="centered error">{error}</div>;
  if (!boardId) return <div className="centered">Lade…</div>;

  return <PublicInner boardId={boardId} title={title} shareToken={token} />;
}

function PublicInner({
  boardId,
  title,
  shareToken,
}: {
  boardId: string;
  title: string;
  shareToken: string;
}) {
  const { yboard, elements, connections, peers } = useYBoard(boardId, {
    name: 'Gast',
    shareToken,
  });

  return (
    <div className="board-view">
      <header className="board-topbar">
        <strong>{title}</strong>
        <span className="readonly-badge">Nur Ansicht</span>
        <div className="spacer" />
        <span className="muted small">Geteilt via Visual Canvas Tool</span>
      </header>
      <Canvas
        yboard={yboard}
        ops={null}
        elements={elements}
        connections={connections}
        peers={peers}
        readOnly
      />
    </div>
  );
}
