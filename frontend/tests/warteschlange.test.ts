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

// --- Training ohne Netz starten (2026-11-21) -------------------------------

const START = {
  name: 'Legs B',
  plan_day_id: 4,
  uebungen: [
    { exercise_id: 11, saetze: 2, wdh: 8, gewicht_kg: 40 },
    { exercise_id: 12, saetze: 1, wdh: 12, gewicht_kg: null },
  ],
  namen: { 11: 'Kniebeuge', 12: 'Wadenheben' },
};

test('offline gestartet: Training und geplante Saetze kommen in Reihenfolge beim Dienst an', async () => {
  const w = await laden();
  const o = await import('../src/offlinetraining');
  const lokal = o.offlineStarten(START);
  assert.ok(lokal.id < 0);
  assert.equal(lokal.sets.length, 3);
  assert.ok(lokal.sets.every(s => !s.is_completed && s.id < 0));
  assert.deepEqual(o.lokalLaden(lokal.id)?.name, 'Legs B');

  // Ersten Satz offline abhaken: PUT auf seine Ersatznummer.
  w.einreihen({ method: 'PUT', path: `/workouts/sets/${lokal.sets[0].id}`, body: { is_completed: true } });

  antworten.push({ status: 201, body: { id: 50 } });
  for (let i = 0; i < 3; i++) antworten.push({ status: 201, body: { id: 101 + i } });
  antworten.push({ status: 200, body: {} });
  const bilanz = await w.abspielen();

  assert.equal(bilanz.erledigt, 5);
  assert.equal(aufrufe[0].path, '/workouts');
  assert.equal((aufrufe[0].body as any).prefill, false, 'sonst legt der Dienst eigene Platzhalter daneben');
  assert.deepEqual(aufrufe.slice(1, 4).map(a => a.path), ['/workouts/50/sets', '/workouts/50/sets', '/workouts/50/sets']);
  assert.equal((aufrufe[1].body as any).is_completed, false);
  assert.equal(aufrufe[4].path, '/workouts/sets/101');
  assert.equal(o.lokalLaden(lokal.id), null, 'die lokale Kopie hat nach dem Nachtragen ausgedient');
});

test('offline ohne bekannte Uebungen startet nichts und sagt warum', async () => {
  await laden();
  const o = await import('../src/offlinetraining');
  assert.throws(() => o.offlineStarten({ ...START, uebungen: [] }), /Vorschlag/);
  assert.equal(speicher.get('fitness-warteschlange-v1') ?? '[]', '[]');
});

test('eine Aenderung an einer Ersatznummer geht nie direkt an den Dienst', async () => {
  // Vorher: Netz wieder da, Schlange noch nicht nachgetragen, PUT auf /sets/-5
  // ging direkt los, bekam 404 und war weg.
  const w = await laden();
  const { api } = await import('../src/api');
  antworten.push({ status: 404, body: { error: 'Satz nicht gefunden' } });
  // Gegen den alten Stand wirft dieser Aufruf (Direktweg, 404 ist kein Netzfehler).
  await assert.doesNotReject(api.putRobust('/workouts/sets/-5', { is_completed: true }));
  await new Promise(r => setTimeout(r, 0));
  // Er lief ueber die Schlange: dort wird ein 404 abgelegt, nicht geworfen.
  assert.equal(w.abgelehnt().length, 1);
  assert.equal(w.abgelehnt()[0].path, '/workouts/sets/-5');
});

test('der gemerkte Vorschlag traegt seinen Stand', async () => {
  const o = await import('../src/offlinetraining');
  o.jetztMerken({ titel: 'Push A', uebungen: [] } as any);
  const v = o.jetztAusVorrat();
  assert.equal(v?.jetzt.titel, 'Push A');
  assert.ok(v && !Number.isNaN(Date.parse(v.am)));
});

// --- Muskelkarte (2026-11-21) ----------------------------------------------

test('eine Region zeigt ihre am staerksten belastete Gruppe', async () => {
  const { regionen } = await import('../src/components/MuscleMap');
  const g = (gruppe: string, region: string, frische: number, stunden: number | null, bereit = 0) =>
    ({ gruppe, name: gruppe, region, frische, stunden_seit: stunden, bereit_in_stunden: bereit, letzte_saetze: 0 });
  const r = regionen([
    g('front_delta', 'shoulders', 0.95, 30),
    g('seit_delta', 'shoulders', 0.3, 10, 20),
    g('hinter_delta', 'shoulders', 1, null),
    g('waden', 'calves', 1, null),
    g('brust', 'chest', 0.7, 20, 8),
  ]);
  assert.equal(r.shoulders.zustand, 'belastet');
  assert.equal(r.shoulders.bereitInStunden, 20);
  assert.equal(r.calves.zustand, 'ruht', 'nie trainiert ist nicht "bereit"');
  assert.equal(r.chest.zustand, 'erholt');
});
