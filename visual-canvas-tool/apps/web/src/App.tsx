import { useEffect, useState } from 'react';
import { useAuth } from './authStore';
import { Login } from './components/Login';
import { Dashboard } from './components/Dashboard';
import { BoardView } from './components/BoardView';
import { PublicBoardView } from './components/PublicBoardView';

/** Minimaler Hash-Router (kein zusaetzliches Routing-Paket noetig). */
function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash || '#/');
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || '#/');
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
}

export function navigate(path: string) {
  window.location.hash = path;
}

export function App() {
  const { user, loading, init } = useAuth();
  const hash = useHashRoute();

  useEffect(() => {
    init();
  }, [init]);

  // Oeffentlicher Lese-Link ist ohne Login erreichbar (/F640/).
  const publicMatch = hash.match(/^#\/public\/([^/]+)/);
  if (publicMatch) return <PublicBoardView token={publicMatch[1]} />;

  if (loading) return <div className="centered">Lade…</div>;
  if (!user) return <Login />;

  const boardMatch = hash.match(/^#\/board\/([^/]+)/);
  if (boardMatch) return <BoardView boardId={boardMatch[1]} />;

  return <Dashboard />;
}
