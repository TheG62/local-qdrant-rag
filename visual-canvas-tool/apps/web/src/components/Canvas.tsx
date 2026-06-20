import { useCallback, useRef, useState } from 'react';
import type { YBoard, PresenceUser } from '../yboard';
import type { BoardOps } from '../boardOps';
import type { CanvasElement, Connection } from '../types';
import { Card } from './Card';
import { v4 as uuid } from '../uuid';

interface Viewport {
  x: number;
  y: number;
  scale: number;
}

interface DragState {
  id: string;
  startX: number;
  startY: number;
  origX: number;
  origY: number;
}

interface ConnectState {
  source: string;
  toX: number;
  toY: number;
}

export function Canvas({
  yboard,
  ops,
  elements,
  connections,
  peers,
  readOnly,
}: {
  yboard: YBoard | null;
  ops: BoardOps | null;
  elements: CanvasElement[];
  connections: Connection[];
  peers: PresenceUser[];
  readOnly: boolean;
}) {
  const [vp, setVp] = useState<Viewport>({ x: 0, y: 0, scale: 1 });
  const [selected, setSelected] = useState<string | null>(null);
  const surfaceRef = useRef<HTMLDivElement>(null);
  const pan = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const drag = useRef<DragState | null>(null);
  const [connect, setConnect] = useState<ConnectState | null>(null);

  const toWorld = useCallback(
    (clientX: number, clientY: number) => {
      const rect = surfaceRef.current!.getBoundingClientRect();
      return {
        x: (clientX - rect.left - vp.x) / vp.scale,
        y: (clientY - rect.top - vp.y) / vp.scale,
      };
    },
    [vp],
  );

  // Zoom (/F230/) — fokussiert auf Cursorposition.
  const onWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const rect = surfaceRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    const newScale = Math.min(3, Math.max(0.2, vp.scale * factor));
    setVp({
      scale: newScale,
      x: mx - ((mx - vp.x) / vp.scale) * newScale,
      y: my - ((my - vp.y) / vp.scale) * newScale,
    });
  };

  const onPointerDownSurface = (e: React.PointerEvent) => {
    if (e.target !== surfaceRef.current && e.target !== surfaceRef.current?.firstChild) return;
    setSelected(null);
    pan.current = { x: e.clientX, y: e.clientY, vx: vp.x, vy: vp.y };
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    // Live-Cursor an Mitbearbeitende senden (/F600/).
    if (yboard) {
      const w = toWorld(e.clientX, e.clientY);
      yboard.provider.awareness.setLocalStateField('cursor', { x: w.x, y: w.y });
    }
    if (pan.current) {
      setVp((v) => ({
        ...v,
        x: pan.current!.vx + (e.clientX - pan.current!.x),
        y: pan.current!.vy + (e.clientY - pan.current!.y),
      }));
      return;
    }
    if (drag.current && ops) {
      const dx = (e.clientX - drag.current.startX) / vp.scale;
      const dy = (e.clientY - drag.current.startY) / vp.scale;
      ops.update(drag.current.id, {
        x: Math.round(drag.current.origX + dx),
        y: Math.round(drag.current.origY + dy),
      });
      return;
    }
    if (connect) {
      const w = toWorld(e.clientX, e.clientY);
      setConnect({ ...connect, toX: w.x, toY: w.y });
    }
  };

  const onPointerUp = (e: React.PointerEvent) => {
    pan.current = null;
    drag.current = null;
    if (connect && ops) {
      // Ziel-Element unter dem Cursor finden.
      const target = elements.find(
        (el) =>
          el.id !== connect.source &&
          connect.toX >= el.x &&
          connect.toX <= el.x + el.width &&
          connect.toY >= el.y &&
          connect.toY <= el.y + el.height,
      );
      if (target) {
        ops.addConnection({
          id: uuid(),
          source: connect.source,
          target: target.id,
          style: 'curved',
        });
      }
      setConnect(null);
    }
    void e;
  };

  const startDrag = (id: string, e: React.PointerEvent) => {
    if (readOnly || !ops) return;
    const el = elements.find((x) => x.id === id);
    if (!el) return;
    ops.bringToFront(id);
    setSelected(id);
    drag.current = {
      id,
      startX: e.clientX,
      startY: e.clientY,
      origX: el.x,
      origY: el.y,
    };
  };

  const startConnect = (id: string, e: React.PointerEvent) => {
    if (readOnly) return;
    const w = toWorld(e.clientX, e.clientY);
    setConnect({ source: id, toX: w.x, toY: w.y });
  };

  const center = (el: CanvasElement) => ({
    x: el.x + el.width / 2,
    y: el.y + el.height / 2,
  });
  const byId = (id: string) => elements.find((e) => e.id === id);

  return (
    <div
      ref={surfaceRef}
      className="canvas-surface"
      onWheel={onWheel}
      onPointerDown={onPointerDownSurface}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      <div
        className="canvas-world"
        style={{ transform: `translate(${vp.x}px, ${vp.y}px) scale(${vp.scale})` }}
      >
        {/* Verbindungen (/F500/) */}
        <svg className="connections-layer" width="100000" height="100000">
          {connections.map((c) => {
            const s = byId(c.source);
            const t = byId(c.target);
            if (!s || !t) return null;
            const a = center(s);
            const b = center(t);
            const mx = (a.x + b.x) / 2;
            return (
              <path
                key={c.id}
                d={`M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`}
                className="connection-path"
                onDoubleClick={() => ops?.removeConnection(c.id)}
              />
            );
          })}
          {connect && byId(connect.source) && (
            <line
              x1={center(byId(connect.source)!).x}
              y1={center(byId(connect.source)!).y}
              x2={connect.toX}
              y2={connect.toY}
              className="connection-path pending"
            />
          )}
        </svg>

        {elements
          .slice()
          .sort((a, b) => (a.z || 0) - (b.z || 0))
          .map((el) => (
            <Card
              key={el.id}
              element={el}
              selected={selected === el.id}
              readOnly={readOnly}
              ops={ops}
              onStartDrag={startDrag}
              onStartConnect={startConnect}
              onSelect={setSelected}
            />
          ))}

        {/* Cursor der Mitbearbeitenden (/F600/) */}
        {peers.map(
          (p) =>
            p.cursor && (
              <div
                key={p.clientId}
                className="peer-cursor"
                style={{ left: p.cursor.x, top: p.cursor.y, color: p.color }}
              >
                ▶<span style={{ background: p.color }}>{p.name}</span>
              </div>
            ),
        )}
      </div>

      <div className="zoom-controls">
        <button onClick={() => setVp((v) => ({ ...v, scale: Math.min(3, v.scale * 1.2) }))}>
          +
        </button>
        <span>{Math.round(vp.scale * 100)}%</span>
        <button onClick={() => setVp((v) => ({ ...v, scale: Math.max(0.2, v.scale / 1.2) }))}>
          −
        </button>
        <button onClick={() => setVp({ x: 0, y: 0, scale: 1 })}>⌖</button>
      </div>
    </div>
  );
}
