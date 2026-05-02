import fs from "fs";
import path from "path";

const DATA_DIR = path.join(process.cwd(), "data");

function readJson<T>(filePath: string): T {
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw) as T;
}

export interface Session {
  id: number;
  started_at: string;
  ended_at: string;
  notes: string | null;
}

export interface SessionEvent {
  id: number;
  session_id: number;
  timestamp: string;
  state: string;
  dss: number | null;
  valence: number | null;
  arousal: number | null;
  dominance: number | null;
  intervention_clip: string | null;
}

export interface TimeseriesPoint {
  timestamp: string;
  state: string;
  dss: number;
  valence: number | null;
  arousal: number | null;
  dominance: number | null;
}

export interface Intervention {
  id: number;
  event_id: number;
  session_id: number;
  started_at: string;
  ended_at: string | null;
  clip_path: string | null;
  pre_dss: number;
  post_dss: number | null;
  effective: boolean | null;
}

export interface TrendData {
  total_sessions: number;
  total_interventions: number;
  effective_interventions: number;
  effective_rate_percent: number;
  disturbances_per_night: number[];
  effectiveness_by_night: number[];
  dates: string[];
  state_minutes_per_night?: {
    listening: number[];
    flagged: number[];
    intervening: number[];
  };
}

export interface Manifest {
  exported_at: string;
  session_ids: number[];
}

export interface NightData {
  session: Session;
  events: SessionEvent[];
  timeseries: TimeseriesPoint[];
  interventions: Intervention[];
}

export function getManifest(): Manifest {
  return readJson<Manifest>(path.join(DATA_DIR, "manifest.json"));
}

export function getSessions(): Session[] {
  return readJson<Session[]>(path.join(DATA_DIR, "sessions.json"));
}

export function getTrends(): TrendData {
  return readJson<TrendData>(path.join(DATA_DIR, "trends.json"));
}

export function getRecentInterventions(): Intervention[] {
  return readJson<Intervention[]>(path.join(DATA_DIR, "interventions-recent.json"));
}

export function getNightData(sessionId: string | number): NightData {
  const sessionDir = path.join(DATA_DIR, "sessions", String(sessionId));
  const session = getSessions().find((s) => s.id === Number(sessionId))!;
  const events = readJson<SessionEvent[]>(path.join(sessionDir, "events.json"));
  const timeseries = readJson<TimeseriesPoint[]>(path.join(sessionDir, "timeseries.json"));
  const interventions = readJson<Intervention[]>(path.join(sessionDir, "interventions.json"));
  return { session, events, timeseries, interventions };
}

export function getLastSession(): Session {
  const sessions = getSessions();
  return sessions[0];
}
