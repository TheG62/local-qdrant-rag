/** Mutationen auf dem Yjs-Board-Dokument (konfliktfrei synchronisiert). */
import type { YBoard } from './yboard';
import type { CanvasElement, Connection } from './types';

export function makeOps(yb: YBoard) {
  const { elements, connections, doc } = yb;
  return {
    add(el: CanvasElement) {
      elements.set(el.id, el);
    },
    update(id: string, patch: Partial<CanvasElement>) {
      const cur = elements.get(id);
      if (cur) elements.set(id, { ...cur, ...patch });
    },
    remove(id: string) {
      doc.transact(() => {
        elements.delete(id);
        // verwaiste Verbindungen entfernen (/F520/)
        [...connections.values()].forEach((c) => {
          if (c.source === id || c.target === id) connections.delete(c.id);
        });
      });
    },
    addConnection(c: Connection) {
      connections.set(c.id, c);
    },
    removeConnection(id: string) {
      connections.delete(id);
    },
    bringToFront(id: string) {
      const maxZ = Math.max(0, ...[...elements.values()].map((e) => e.z || 0));
      this.update(id, { z: maxZ + 1 });
    },
  };
}

export type BoardOps = ReturnType<typeof makeOps>;
