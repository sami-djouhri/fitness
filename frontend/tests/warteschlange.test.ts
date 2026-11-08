/**
 * Die Offline-Warteschlange gegen die drei Wege, auf denen sie ein Training
 * verlor (2026-11-03). Jeder Test faellt gegen den Stand davor.
 */
import { test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// --- Browser-Ersatz: localStorage, window, navigator -----------------------
const speicher = new Map<string, string>();
(globalThis as any).localStorage = {
  getItem: (k: string) => speicher.get(k) ?? null,
  setItem: (k: string, v: string) => { speicher.set(k, v); },
  removeItem: (k: string) => { speicher.delete(k); },
};
(globalThis as any).window = { addEventListener() {} };
Object.defineProperty(globalThis, 'navigator', { value: { onLine: false }, configurable: true });

type Antwort = { status: number; body?: unknown; redirected?: boolean };
let antworten: Antwort[] = [];
let aufrufe: { method: string; path: string; body: unknown }[] = [];
(globalThis as any).fetch = async (url: string, init: any) => {
  aufrufe.push({ method: init.method, path: url.replace(/^\/api/, ''), body: init.body ? JSON.parse(init.body) : undefined });
  const a = antworten.shift();
  if (!a) throw new TypeError('Failed to fetch');
  return {
    ok: a.status >= 200 && a.status < 300,
    status: a.status,
    redirected: a.redirected ?? false,
    json: async () => a.body,
  };
};

// Jeder Test braucht ein frisch geladenes Modul, sonst traegt der Zaehler im
// Speicher des Moduls von einem Test zum naechsten.
async function laden() {
  // esbuild buendelt statisch; ein frisches Modul simuliert hier ein
  // Neuladen der Seite, und das geht nur ueber den Zaehler-Ruecksetzer.
  const m = await import('../src/warteschlange');
  m.__nurFuerTests_neuLaden();
  return m;
}

beforeEach(() => {
  speicher.clear();
  antworten = [];
  aufrufe = [];
});

test('eine aufgeloeste Ersatznummer trifft nicht die laengere mit gleichem Anfang', async () => {
  const w = await laden();
  for (let i = 0; i < 12; i++) {
    const id = w.naechsteErsatznummer();
    w.einreihen({ method: 'POST', path: '/workouts/7/sets', body: { reps: 8 }, ersatzId: id });
  }
  // Satz -12 abhaken. Vorher wurde daraus beim Aufloesen von -1 die 1012.
  w.einreihen({ method: 'PUT', path: '/workouts/sets/-12', body: { is_completed: true } });
  for (let i = 0; i < 12; i++) antworten.push({ status: 201, body: { id: 101 + i } });
  antworten.push({ status: 200, body: {} });

  await w.abspielen();
  const put = aufrufe.find(a => a.method === 'PUT')!;
  assert.equal(put.path, '/workouts/sets/112');
});

test('nach dem Neuladen vergibt der Zaehler keine Nummer doppelt', async () => {
  let w = await laden();
  const erste = w.naechsteErsatznummer();
  w.einreihen({ method: 'POST', path: '/workouts/7/sets', body: {}, ersatzId: erste });
  w.einreihen({ method: 'PUT', path: `/workouts/sets/${erste}`, body: { reps: 9 } });

  w = await laden(); // Seite neu geladen, Schlange liegt noch im Speicher
  const zweite = w.naechsteErsatznummer();
  assert.notEqual(zweite, erste);
});

test('ein 502 beim Nachtragen haelt die Schlange an, statt sie zu leeren', async () => {
  const w = await laden();
  w.einreihen({ method: 'PUT', path: '/workouts/sets/5', body: { reps: 8 } });
  w.einreihen({ method: 'PUT', path: '/workouts/sets/6', body: { reps: 8 } });
  antworten.push({ status: 502 });

  const bilanz = await w.abspielen();
  assert.equal(bilanz.verworfen, 0);
  assert.equal(w.anzahlWartend(), 2);
});

test('eine umgeleitete Antwort (Anmeldeseite) zaehlt nicht als nachgetragen', async () => {
  const w = await laden();
  const id = w.naechsteErsatznummer();
  w.einreihen({ method: 'POST', path: '/workouts/7/sets', body: {}, ersatzId: id });
  antworten.push({ status: 200, body: undefined, redirected: true });

  const bilanz = await w.abspielen();
  assert.equal(bilanz.erledigt, 0);
  assert.equal(w.anzahlWartend(), 1);
});

test('ein fachlich abgelehnter Auftrag verschwindet nicht spurlos', async () => {
  const w = await laden();
  w.einreihen({ method: 'PUT', path: '/workouts/sets/5', body: { reps: 8 } });
  antworten.push({ status: 422, body: { detail: 'reps' } });

  const bilanz = await w.abspielen();
  assert.equal(bilanz.verworfen, 1);
  assert.equal(w.anzahlWartend(), 0);
  const abgelehnt = w.abgelehnt();
  assert.equal(abgelehnt.length, 1);
  assert.equal(abgelehnt[0].status, 422);
  assert.equal(abgelehnt[0].path, '/workouts/sets/5');
});

test('Ersatznummern im Rumpf werden ersetzt, andere Zahlen nicht', async () => {
  const w = await laden();
  const id = w.naechsteErsatznummer();
  w.einreihen({ method: 'POST', path: '/workouts/7/sets', body: {}, ersatzId: id });
  w.einreihen({ method: 'PUT', path: '/workouts/sets/9', body: { group_id: id, reps: 12 } });
  antworten.push({ status: 201, body: { id: 300 } }, { status: 200, body: {} });

  await w.abspielen();
  assert.deepEqual(aufrufe[1].body, { group_id: 300, reps: 12 });
});
