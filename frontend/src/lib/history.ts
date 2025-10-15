// Local activity history store backed by localStorage with in-memory cache

export type HistoryEventType = 'plan.created' | 'task.created' | 'task.updated' | 'task.deleted' | 'task.status';

export interface HistoryEvent<T = any> {
  id: string;
  timestamp: number;
  type: HistoryEventType;
  taskId: string | number;
  summary: string;
  before?: Partial<T>;
  after?: Partial<T>;
  batchId?: string;
  // Optional payloads for plan snapshots
  planId?: string;
  plan?: any;
}

export interface ListFilters {
  limit?: number;
  offset?: number;
  types?: HistoryEventType[];
  taskId?: string | number;
  search?: string;
}

const STORAGE_KEY = 'taskflow:history:v1';
const MAX_EVENTS = 2000;

let memoryCache: HistoryEvent[] | null = null;

function loadFromStorage(): HistoryEvent[] {
  if (memoryCache) return memoryCache;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      memoryCache = [];
      return memoryCache;
    }
    const parsed: HistoryEvent[] = JSON.parse(raw);
    memoryCache = Array.isArray(parsed) ? parsed : [];
    return memoryCache;
  } catch {
    // If localStorage is not available or JSON is corrupted, fallback to memory only
    memoryCache = memoryCache || [];
    return memoryCache;
  }
}

function saveToStorage(events: HistoryEvent[]): void {
  memoryCache = events;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
    // Notify listeners
    window.dispatchEvent(new CustomEvent('taskflow:history:changed'));
  } catch {
    // Swallow quota or availability errors; keep memory cache as source of truth
  }
}

export function generateId(): string {
  // Simple UUID v4-ish
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function appendEvent(event: HistoryEvent): void {
  const events = loadFromStorage();
  const next = [...events, event];
  pruneInPlace(next, MAX_EVENTS);
  saveToStorage(next);
}

export function appendEvents(newEvents: HistoryEvent[]): void {
  if (!newEvents.length) return;
  const events = loadFromStorage();
  const next = events.concat(newEvents);
  pruneInPlace(next, MAX_EVENTS);
  saveToStorage(next);
}

export function listEvents(filters: ListFilters = {}): HistoryEvent[] {
  const events = loadFromStorage().slice().reverse(); // newest first
  let filtered = events;
  if (filters.types && filters.types.length > 0) {
    const set = new Set(filters.types);
    filtered = filtered.filter(e => set.has(e.type));
  }
  if (filters.taskId !== undefined) {
    filtered = filtered.filter(e => String(e.taskId) === String(filters.taskId));
  }
  if (filters.search && filters.search.trim()) {
    const q = filters.search.trim().toLowerCase();
    filtered = filtered.filter(e => e.summary.toLowerCase().includes(q));
  }
  const offset = filters.offset || 0;
  const limit = filters.limit || filtered.length;
  return filtered.slice(offset, offset + limit);
}

export function clearEvents(): void {
  saveToStorage([]);
}

export function prune(maxEvents: number = MAX_EVENTS): void {
  const events = loadFromStorage();
  const next = events.slice(-maxEvents);
  saveToStorage(next);
}

function pruneInPlace(arr: HistoryEvent[], maxEvents: number): void {
  if (arr.length > maxEvents) {
    const excess = arr.length - maxEvents;
    arr.splice(0, excess);
  }
}

export function diffObjects<T extends Record<string, any>>(before: Partial<T> | undefined, after: Partial<T> | undefined): { before?: Partial<T>; after?: Partial<T> } {
  if (!before && !after) return {};
  if (!before) return { after };
  if (!after) return { before };
  const changedKeys = new Set<string>();
  const keys = new Set<string>([...Object.keys(before), ...Object.keys(after)]);
  keys.forEach(k => {
    const a = (before as any)[k];
    const b = (after as any)[k];
    const isObj = (v: any) => v && typeof v === 'object';
    const equal = isObj(a) || isObj(b) ? JSON.stringify(a) === JSON.stringify(b) : a === b;
    if (!equal) changedKeys.add(k);
  });
  if (changedKeys.size === 0) return {};
  const b: any = {};
  const a: any = {};
  changedKeys.forEach(k => {
    if (k in before) b[k] = (before as any)[k];
    if (k in after) a[k] = (after as any)[k];
  });
  return { before: b, after: a };
}

export function formatEvent(e: HistoryEvent): string {
  const time = new Date(e.timestamp).toLocaleTimeString();
  return `[${time}] ${e.type} • ${e.summary}`;
}

export function recordTaskEvent<T = any>(params: Omit<HistoryEvent<T>, 'id' | 'timestamp'>): void {
  appendEvent({
    id: generateId(),
    timestamp: Date.now(),
    ...params,
  });
}


