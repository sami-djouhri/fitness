import { einreihen, naechsteErsatznummer } from './warteschlange';

const BASE = '/api';

/**
 * Nach dieser Zeit gilt eine Anfrage als gescheitert. Ohne Grenze haengt im
 * Gym mit einem Balken Empfang die Oberflaeche, bis der Browser von selbst
 * aufgibt, und der Nutzer tippt denselben Satz zweimal.
 */
const ZEITGRENZE_MS = 8000;

export class NetzFehler extends Error {}

function istNetzFehler(fehler: unknown): boolean {
  // fetch wirft TypeError bei fehlender Verbindung, AbortError beim Zeitablauf.
  return fehler instanceof TypeError
    || (fehler instanceof DOMException && fehler.name === 'AbortError');
}

async function einmalSenden<T>(method: string, path: string, body?: unknown): Promise<T> {
  const abbruch = new AbortController();
  const wecker = setTimeout(() => abbruch.abort(), ZEITGRENZE_MS);
  try {
    const res = await fetch(BASE + path, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : {},
      body: body ? JSON.stringify(body) : undefined,
      signal: abbruch.signal,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || res.statusText);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  } finally {
    clearTimeout(wecker);
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  try {
    return await einmalSenden<T>(method, path, body);
  } catch (fehler) {
    if (!istNetzFehler(fehler)) throw fehler;
    // Ein Versuch mehr: im Gym bricht die Verbindung eher kurz weg, als dass
    // sie ganz fehlt.
    try {
      return await einmalSenden<T>(method, path, body);
    } catch (zweiterFehler) {
      if (!istNetzFehler(zweiterFehler)) throw zweiterFehler;
      throw new NetzFehler('Keine Verbindung');
    }
  }
}

/**
 * Mutation, die einen Netzausfall uebersteht: scheitert sie am Netz, wandert
 * sie ins Journal und wird spaeter nachgetragen. ``ersatz`` liefert das, was
 * die Oberflaeche in der Zwischenzeit anzeigt.
 */
async function mutation<T>(
  method: 'POST' | 'PUT' | 'DELETE',
  path: string,
  body: unknown | undefined,
  ersatz?: (ersatzId: number) => T,
): Promise<T> {
  try {
    return await request<T>(method, path, body);
  } catch (fehler) {
    if (!(fehler instanceof NetzFehler)) throw fehler;
    const ersatzId = ersatz ? naechsteErsatznummer() : undefined;
    einreihen({ method, path, body, ersatzId });
    if (ersatz && ersatzId != null) return ersatz(ersatzId);
    return undefined as T;
  }
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),

  /** Wie ``post``, faellt bei Netzausfall aber auf das Journal zurueck. */
  postRobust: <T>(path: string, body: unknown, ersatz: (ersatzId: number) => T) =>
    mutation<T>('POST', path, body, ersatz),
  putRobust: <T>(path: string, body: unknown) => mutation<T>('PUT', path, body),
  delRobust: (path: string) => mutation<void>('DELETE', path, undefined),
};
