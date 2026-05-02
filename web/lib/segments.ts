export interface Segment {
  state: string;
  startT: number;
  endT: number;
}

export function buildSegments(
  events: Array<{ timestamp: string; state: string }>,
  sessionStart: string
): Segment[] {
  if (events.length === 0) return [];
  const start = new Date(sessionStart).getTime();
  const segs: Segment[] = [];

  for (let i = 0; i < events.length; i++) {
    const startT = (new Date(events[i].timestamp).getTime() - start) / 1000;
    const endT =
      i + 1 < events.length
        ? (new Date(events[i + 1].timestamp).getTime() - start) / 1000
        : startT + 120;
    if (segs.length > 0 && segs[segs.length - 1].state === events[i].state) {
      segs[segs.length - 1].endT = endT;
    } else {
      segs.push({ state: events[i].state, startT, endT });
    }
  }
  return segs;
}
