import { useEffect, useMemo, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../authStore';
import { navigate } from '../App';
import type { Board } from '../types';

export function Dashboard() {
  const { user, logout } = useAuth();
  const [boards, setBoards] = useState<Board[]>([]);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<{ boardId: string; title: string; snippet: string }[]>([]);
  const [showTrash, setShowTrash] = useState(false);
  const [trash, setTrash] = useState<Board[]>([]);

  const load = async () => {
    const { boards } = await api.listBoards();
    setBoards(boards);
  };
  useEffect(() => {
    load();
  }, []);

  // Volltextsuche (/F900/) — debounced.
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      const { results } = await api.search(query);
      setResults(results);
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  const roots = useMemo(() => boards.filter((b) => !b.parentId), [boards]);
  const childrenOf = (id: string) => boards.filter((b) => b.parentId === id);

  const createBoard = async () => {
    const title = prompt('Titel des neuen Boards?');
    if (title === null) return;
    const { board } = await api.createBoard(title || 'Neues Board');
    await load();
    navigate(`#/board/${board.id}`);
  };

  const openTrash = async () => {
    const { boards } = await api.trash();
    setTrash(boards);
    setShowTrash(true);
  };

  const deleteAccount = async () => {
    if (!confirm('Konto und alle Daten unwiderruflich loeschen? (DSGVO Art. 17)')) return;
    await api.deleteAccount();
    logout();
  };

  return (
    <div className="dashboard">
      <header className="topbar">
        <strong>Visual Canvas Tool</strong>
        <input
          className="search"
          placeholder="Suchen in allen Boards…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="spacer" />
        <span className="muted">{user?.name}</span>
        <button className="ghost" onClick={openTrash}>
          Papierkorb
        </button>
        <button className="ghost" onClick={deleteAccount}>
          Konto loeschen
        </button>
        <button className="ghost" onClick={logout}>
          Abmelden
        </button>
      </header>

      <main className="dash-main">
        {results.length > 0 ? (
          <section>
            <h2>Suchergebnisse</h2>
            {results.map((r) => (
              <div
                key={r.boardId}
                className="search-result"
                onClick={() => navigate(`#/board/${r.boardId}`)}
              >
                <strong>{r.title}</strong>
                <span className="muted">…{r.snippet}…</span>
              </div>
            ))}
          </section>
        ) : (
          <section>
            <div className="dash-head">
              <h2>Deine Boards</h2>
              <button onClick={createBoard}>+ Neues Board</button>
            </div>
            <div className="board-grid">
              {roots.map((b) => (
                <div
                  key={b.id}
                  className="board-card"
                  onClick={() => navigate(`#/board/${b.id}`)}
                >
                  <div className="board-card-icon">{b.isHome ? '🏠' : '🗂️'}</div>
                  <div className="board-card-title">{b.title}</div>
                  <div className="muted small">
                    {childrenOf(b.id).length} Sub-Board(s)
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      {showTrash && (
        <div className="modal-overlay" onClick={() => setShowTrash(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Papierkorb</h3>
            {trash.length === 0 && <p className="muted">Leer.</p>}
            {trash.map((b) => (
              <div key={b.id} className="trash-row">
                <span>{b.title}</span>
                <button
                  className="ghost"
                  onClick={async () => {
                    await api.restoreBoard(b.id);
                    await openTrash();
                    await load();
                  }}
                >
                  Wiederherstellen
                </button>
              </div>
            ))}
            <button className="ghost" onClick={() => setShowTrash(false)}>
              Schliessen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
