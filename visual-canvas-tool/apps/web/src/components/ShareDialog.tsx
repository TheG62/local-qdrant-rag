import { useEffect, useState } from 'react';
import { api } from '../api';
import type { Board, Share } from '../types';

/** Freigabe & oeffentlicher Lese-Link (/F630/, /F640/, /MK50/). */
export function ShareDialog({ board, onClose }: { board: Board; onClose: () => void }) {
  const [shares, setShares] = useState<Share[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<'editor' | 'viewer'>('viewer');

  const load = async () => setShares((await api.listShares(board.id)).shares);
  useEffect(() => {
    load();
  }, []);

  const publicShare = shares.find((s) => s.publicToken);
  const publicUrl = publicShare
    ? `${location.origin}${location.pathname}#/public/${publicShare.publicToken}`
    : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>„{board.title}" teilen</h3>

        <div className="share-add">
          <input
            type="email"
            placeholder="E-Mail einladen"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <select value={role} onChange={(e) => setRole(e.target.value as 'editor' | 'viewer')}>
            <option value="viewer">Betrachter</option>
            <option value="editor">Bearbeiter</option>
          </select>
          <button
            onClick={async () => {
              if (!email) return;
              await api.share(board.id, { email, role });
              setEmail('');
              load();
            }}
          >
            Einladen
          </button>
        </div>

        <ul className="share-list">
          {shares
            .filter((s) => s.email)
            .map((s) => (
              <li key={s.id}>
                <span>
                  {s.email} · {s.role === 'editor' ? 'Bearbeiter' : 'Betrachter'}
                </span>
                <button
                  className="mini"
                  onClick={async () => {
                    await api.removeShare(s.id);
                    load();
                  }}
                >
                  ✕
                </button>
              </li>
            ))}
        </ul>

        <hr />
        <h4>Oeffentlicher Lese-Link</h4>
        {publicUrl ? (
          <div className="public-link">
            <input readOnly value={publicUrl} onFocus={(e) => e.target.select()} />
            <button
              className="mini"
              onClick={async () => {
                await api.removeShare(publicShare!.id);
                load();
              }}
            >
              Deaktivieren
            </button>
          </div>
        ) : (
          <button
            onClick={async () => {
              await api.share(board.id, { publicLink: true });
              load();
            }}
          >
            Lese-Link erstellen
          </button>
        )}

        <div className="modal-actions">
          <button className="ghost" onClick={onClose}>
            Schliessen
          </button>
        </div>
      </div>
    </div>
  );
}
