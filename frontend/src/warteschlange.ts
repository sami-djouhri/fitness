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

let naechsteErsatzId = -1;
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

export function naechsteErsatznummer(): number {
  return naechsteErsatzId--;
}

export function einreihen(auftrag: Omit<Auftrag, 'id'>): void {
  const auftraege = lesen();
  auftraege.push({ ...auftrag, id: `${Date.now()}-${auftraege.length}-${Math.random().toString(36).slice(2, 8)}` });
  schreiben(auftraege);
}

/** Ersetzt eine Ersatz-Nummer in allen noch wartenden Auftraegen. */
function ersatzNummerErsetzen(auftraege: Auftrag[], ersatzId: number, echteId: number): Auftrag[] {
  const alt = `/${ersatzId}`;
  const neu = `/${echteId}`;
  return auftraege.map(a => ({
    ...a,
    // Pfade wie /workouts/sets/-3 oder /workouts/-1/sets
    path: a.path.includes(alt) ? a.path.split(alt).join(neu) : a.path,
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

/**
 * Traegt die Warteschlange nach. Bricht beim ersten Netzfehler ab und laesst
 * den Rest stehen, damit die Reihenfolge erhalten bleibt.
 *
 * Ein fachlicher Fehler (4xx) ist etwas anderes als ein Netzfehler: der
 * Auftrag wird nie durchgehen und wird verworfen, sonst blockiert er die
 * Schlange fuer immer.
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

      let rest = auftraege.slice(1);

      if (antwort.ok && auftrag.ersatzId != null) {
        const daten = await antwort.json().catch(() => null);
        const echteId = daten && typeof daten.id === 'number' ? daten.id : null;
        if (echteId != null) {
          rest = ersatzNummerErsetzen(rest, auftrag.ersatzId, echteId);
          aufloeser.forEach(a => a(auftrag.ersatzId!, echteId));
        }
      }

      if (antwort.ok) erledigt++;
      else verworfen++;

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
