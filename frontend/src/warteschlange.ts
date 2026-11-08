/**
 * Offline-Journal fuer schreibende Aufrufe.
 *
 * Das Gym ist der Ort, an dem diese App benutzt wird, und dort ist oft kein
 * Netz. Vorher ging jeder Satz in genau diesem Fall verloren: `api.post` warf
 * eine unbehandelte Rejection, der Satz war weg, ohne Fehlermeldung.
 *
 * Ablauf: schlaegt eine Mutation am Netz fehl, wandert sie hierher und wird
 * spaeter in der urspruenglichen Reihenfolge nachgetragen. Neu angelegte
 * Objekte bekommen bis dahin eine negative Ersatz-Nummer. Sobald der Server
 * die echte liefert, werden noch wartende Auftraege umgeschrieben, die sich
 * auf die Ersatz-Nummer beziehen (Satz anlegen, dann Gewicht aendern).
 *
 * Bewusst localStorage und nicht IndexedDB: die Warteschlange ist klein
 * (ein Trainingsabend), und synchrones Lesen erspart Zustandsgewurschtel beim
 * Start.
 */

const SPEICHER_SCHLUESSEL = 'fitness-warteschlange-v1';
const ZAEHLER_SCHLUESSEL = 'fitness-ersatznummer-v1';
const ABGELEHNT_SCHLUESSEL = 'fitness-warteschlange-abgelehnt-v1';
/** So viele abgelehnte Auftraege bleiben zum Nachsehen liegen. */
const ABGELEHNT_MAX = 50;

/** Ein Auftrag, den der Dienst fachlich abgelehnt hat (4xx). */
export interface Abgelehnt extends Auftrag {
  status: number;
  /** Was der Dienst dazu sagte, gekuerzt. */
  meldung: string;
  am: string;
}

export interface Auftrag {
  id: string;
  method: 'POST' | 'PUT' | 'DELETE';
  path: string;
  body?: unknown;
  /** Ersatz-Nummer, unter der das Ergebnis dieses POST im UI steht. */
  ersatzId?: number;
}

type IdAufloesung = (ersatzId: number, echteId: number) => void;
type Beobachter = (anzahl: number) => void;

const beobachter = new Set<Beobachter>();
const aufloeser = new Set<IdAufloesung>();
let laeuft = false;

function lesen(): Auftrag[] {
  try {
    const rohtext = localStorage.getItem(SPEICHER_SCHLUESSEL);
    return rohtext ? (JSON.parse(rohtext) as Auftrag[]) : [];
  } catch {
    return [];
  }
}

function schreiben(auftraege: Auftrag[]): void {
  try {
    localStorage.setItem(SPEICHER_SCHLUESSEL, JSON.stringify(auftraege));
  } catch {
    // Voller Speicher darf die Erfassung nicht abbrechen. Der Auftrag bleibt
    // dann nur im laufenden Programm und geht beim Neuladen verloren, was
    // immer noch besser ist als ein Absturz mitten im Satz.
  }
  beobachter.forEach(b => b(auftraege.length));
}

export function anzahlWartend(): number {
  return lesen().length;
}

export function beobachten(b: Beobachter): () => void {
  beobachter.add(b);
  b(anzahlWartend());
  return () => beobachter.delete(b);
}

/** Meldet, wenn eine Ersatz-Nummer durch die echte ersetzt wurde. */
export function aufIdAufloesung(a: IdAufloesung): () => void {
  aufloeser.add(a);
  return () => aufloeser.delete(a);
}

/**
 * Die naechste freie Ersatznummer.
 *
 * Steht im Speicher und nicht nur im laufenden Programm. Bis 2026-11-03
 * begann der Zaehler nach jedem Neuladen wieder bei -1; mit Service Worker
 * laedt die Seite auch im Funkloch neu, und zwei Saetze teilten sich dann eine
 * Nummer. Beim Nachtragen landeten die Aenderungen des zweiten beim ersten.
 * Zusaetzlich unter jeder Nummer, die noch in der Schlange steht, damit auch
 * eine Schlange aus der Zeit davor nicht kollidiert.
 */
export function naechsteErsatznummer(): number {
  let naechste = -1;
  try {
    const gespeichert = Number(localStorage.getItem(ZAEHLER_SCHLUESSEL));
    if (Number.isInteger(gespeichert) && gespeichert < 0) naechste = gespeichert;
  } catch {
    // ohne Speicher bleibt es bei der Untergrenze aus der Schlange
  }
  for (const a of lesen()) {
    if (a.ersatzId != null && a.ersatzId <= naechste) naechste = a.ersatzId - 1;
    for (const treffer of a.path.matchAll(/\/(-\d+)(?=\/|\?|$)/g)) {
      const n = Number(treffer[1]);
      if (n <= naechste) naechste = n - 1;
    }
  }
  try {
    localStorage.setItem(ZAEHLER_SCHLUESSEL, String(naechste - 1));
  } catch {
    // s. o.
  }
  return naechste;
}

/** Nur fuer die Tests: ein Neuladen der Seite hat keinen Zustand im Modul. */
export function __nurFuerTests_neuLaden(): void {
  laeuft = false;
}

/** Was der Dienst abgelehnt hat, juengstes zuletzt. */
export function abgelehnt(): Abgelehnt[] {
  try {
    const rohtext = localStorage.getItem(ABGELEHNT_SCHLUESSEL);
    return rohtext ? (JSON.parse(rohtext) as Abgelehnt[]) : [];
  } catch {
    return [];
  }
}

export function abgelehntLeeren(): void {
  try {
    localStorage.removeItem(ABGELEHNT_SCHLUESSEL);
  } catch {
    // nichts zu tun
  }
  beobachter.forEach(b => b(anzahlWartend()));
}

function ablegen(auftrag: Auftrag, status: number, meldung: string): void {
  const liste = [...abgelehnt(), { ...auftrag, status, meldung: meldung.slice(0, 300), am: new Date().toISOString() }];
  try {
    localStorage.setItem(ABGELEHNT_SCHLUESSEL, JSON.stringify(liste.slice(-ABGELEHNT_MAX)));
  } catch {
    // Voller Speicher: dann wenigstens in der Konsole.
    console.warn('Auftrag abgelehnt und nicht ablegbar', auftrag, status, meldung);
  }
}

export function einreihen(auftrag: Omit<Auftrag, 'id'>): void {
  const auftraege = lesen();
  auftraege.push({ ...auftrag, id: `${Date.now()}-${auftraege.length}-${Math.random().toString(36).slice(2, 8)}` });
  schreiben(auftraege);
}

/** Ersetzt eine Ersatz-Nummer in allen noch wartenden Auftraegen. */
function ersatzNummerErsetzen(auftraege: Auftrag[], ersatzId: number, echteId: number): Auftrag[] {
  // Nur ein ganzes Pfadstueck. Bis 2026-11-03 stand hier ein Textersatz
  // von `/-1`, und der traf auch `/-12`: aus `/workouts/sets/-12` wurde
  // `/workouts/sets/1012`, ein fremder Satz oder ein 404, und die Aenderung
  // war weg. Ab zehn offline angelegten Saetzen der Normalfall.
  const muster = new RegExp(`/${ersatzId}(?=/|\\?|$)`, 'g');
  return auftraege.map(a => ({
    ...a,
    // Pfade wie /workouts/sets/-3 oder /workouts/-1/sets
    path: a.path.replace(muster, `/${echteId}`),
    body: a.body ? ersatzNummerImBody(a.body, ersatzId, echteId) : a.body,
  }));
}

function ersatzNummerImBody(body: unknown, ersatzId: number, echteId: number): unknown {
  if (Array.isArray(body)) return body.map(w => ersatzNummerImBody(w, ersatzId, echteId));
  if (body && typeof body === 'object') {
    const kopie: Record<string, unknown> = {};
    for (const [schluessel, wert] of Object.entries(body as Record<string, unknown>)) {
      kopie[schluessel] = wert === ersatzId ? echteId : ersatzNummerImBody(wert, ersatzId, echteId);
    }
    return kopie;
  }
  return body;
}

/** Antworten, nach denen ein spaeterer Versuch gelingen kann. */
function voruebergehend(status: number): boolean {
  return status >= 500 || status === 408 || status === 425 || status === 429;
}

/**
 * Traegt die Warteschlange nach. Bricht beim ersten Netzfehler ab und laesst
 * den Rest stehen, damit die Reihenfolge erhalten bleibt.
 *
 * Ein fachlicher Fehler (4xx) ist etwas anderes als ein Netzfehler: der
 * Auftrag wird nie durchgehen und wird aus der Schlange genommen, sonst
 * blockiert er sie fuer immer. Er wird abgelegt ([abgelehnt]), nicht
 * weggeworfen: bis 2026-11-03 verschwand er ohne jede Spur.
 *
 * Ein 5xx ist KEIN fachlicher Fehler. Bis 2026-11-03 wurde auch er
 * verworfen; ein Neustart des Dienstes waehrend des Nachtragens (502 vom
 * Proxy) leerte damit den Rest eines Trainings. Ebenso eine umgeleitete
 * Antwort: das ist die Anmeldeseite, nicht der Dienst.
 */
export async function abspielen(): Promise<{ erledigt: number; verworfen: number }> {
  if (laeuft) return { erledigt: 0, verworfen: 0 };
  laeuft = true;
  let erledigt = 0;
  let verworfen = 0;
  try {
    for (;;) {
      const auftraege = lesen();
      if (auftraege.length === 0) break;
      const auftrag = auftraege[0];

      let antwort: Response;
      try {
        antwort = await fetch('/api' + auftrag.path, {
          method: auftrag.method,
          headers: auftrag.body ? { 'Content-Type': 'application/json' } : {},
          body: auftrag.body ? JSON.stringify(auftrag.body) : undefined,
        });
      } catch {
        break; // weiter offline, spaeter erneut
      }

      if (voruebergehend(antwort.status) || antwort.redirected) break;

      let rest = auftraege.slice(1);

      if (antwort.ok && auftrag.ersatzId != null) {
        const daten = await antwort.json().catch(() => null);
        const echteId = daten && typeof daten.id === 'number' ? daten.id : null;
        if (echteId != null) {
          rest = ersatzNummerErsetzen(rest, auftrag.ersatzId, echteId);
          aufloeser.forEach(a => a(auftrag.ersatzId!, echteId));
        }
      }

      if (antwort.ok) {
        erledigt++;
      } else {
        verworfen++;
        const meldung = await antwort.json().then(d => JSON.stringify(d)).catch(() => '');
        ablegen(auftrag, antwort.status, meldung);
      }

      schreiben(rest);
    }
  } finally {
    laeuft = false;
  }
  return { erledigt, verworfen };
}

/** Beim Start und bei jeder Rueckkehr des Netzes nachtragen. */
export function nachtragenStarten(): void {
  window.addEventListener('online', () => { void abspielen(); });
  if (navigator.onLine) void abspielen();
}
