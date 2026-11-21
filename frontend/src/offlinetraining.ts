/**
 * Ein Training ohne Netz beginnen.
 *
 * Bis 2026-11-21 ließ sich im Web offline nur ein Satz erfassen, nicht ein
 * Training starten: `POST /workouts` lief über `api.post`, und ohne Netz blieb
 * die Seite mit einer Fehlermeldung stehen. Im Gym ist das genau der Moment,
 * in dem man anfängt.
 *
 * Ablauf, ganz über die vorhandene Warteschlange (`warteschlange.ts`):
 * 1. `POST /workouts` mit `prefill: false` und Ersatznummer W. Ohne
 *    `prefill: false` legte der Dienst beim Nachtragen seine eigenen offenen
 *    Sätze neben die offline erfassten (dieselbe Falle wie in der App 0.1.9).
 * 2. Je geplantem Satz ein `POST /workouts/W/sets` mit `is_completed: false`
 *    und eigener Ersatznummer. Beim Nachtragen wird W im Pfad durch die echte
 *    Kennung ersetzt, Abhaken (`PUT /workouts/sets/<ersatz>`) ebenso.
 * 3. Die Seite zeigt das Training aus einer lokalen Kopie, bis der Dienst die
 *    echte Kennung liefert.
 *
 * Damit die Startseite offline überhaupt etwas zum Starten hat, wird die
 * letzte Antwort von `/training/jetzt` gemerkt. Angezeigt wird sie mit ihrem
 * Stand: ein Vorschlag von gestern ist kein Vorschlag von heute.
 */

import { aufIdAufloesung, einreihen, naechsteErsatznummer } from './warteschlange';
import type { PlanTarget, StartUebung, TrainingJetzt, Workout, WorkoutSet } from './types';

const VORRAT_SCHLUESSEL = 'fitness-jetzt-vorrat-v1';
const LOKAL_SCHLUESSEL = 'fitness-offline-trainings-v1';

// --- Vorrat für die Auskunft "was trainiere ich jetzt" ---------------------

export interface Vorrat {
  jetzt: TrainingJetzt;
  /** ISO-Zeitpunkt der Antwort. */
  am: string;
}

export function jetztMerken(jetzt: TrainingJetzt): void {
  try {
    localStorage.setItem(VORRAT_SCHLUESSEL, JSON.stringify({ jetzt, am: new Date().toISOString() }));
  } catch {
    // Voller Speicher: dann gibt es offline eben keinen Vorschlag.
  }
}

export function jetztAusVorrat(): Vorrat | null {
  try {
    const roh = localStorage.getItem(VORRAT_SCHLUESSEL);
    return roh ? (JSON.parse(roh) as Vorrat) : null;
  } catch {
    return null;
  }
}

// --- Lokale Kopien laufender Offline-Trainings -----------------------------

function alleLokalen(): Record<string, Workout> {
  try {
    const roh = localStorage.getItem(LOKAL_SCHLUESSEL);
    return roh ? (JSON.parse(roh) as Record<string, Workout>) : {};
  } catch {
    return {};
  }
}

function alleSchreiben(alle: Record<string, Workout>): void {
  try {
    localStorage.setItem(LOKAL_SCHLUESSEL, JSON.stringify(alle));
  } catch {
    // s. o.
  }
}

export function lokalSpeichern(w: Workout): void {
  const alle = alleLokalen();
  alle[String(w.id)] = w;
  alleSchreiben(alle);
}

export function lokalLaden(id: number): Workout | null {
  return alleLokalen()[String(id)] ?? null;
}

export function lokalEntfernen(id: number): void {
  const alle = alleLokalen();
  delete alle[String(id)];
  alleSchreiben(alle);
}

// Ist ein offline begonnenes Training beim Dienst angekommen, hat die lokale
// Kopie ausgedient, auch wenn die Trainingsseite gerade nicht offen ist (etwa
// nach dem Beenden im Funkloch).
aufIdAufloesung((ersatzId) => { if (lokalLaden(ersatzId)) lokalEntfernen(ersatzId); });

/** Offline begonnene, noch nicht beendete Trainings (für die Startseite). */
export function laufendeLokale(): Workout[] {
  return Object.values(alleLokalen()).filter(w => !w.finished_at);
}

// --- Starten ---------------------------------------------------------------

export interface OfflineStart {
  name?: string;
  plan_day_id?: number;
  uebungen: StartUebung[];
  /** Anzeigename und Pause je Übung, aus der Auskunft. */
  namen: Record<number, string>;
  pausen?: Record<number, number>;
  bereitschaft?: Record<string, unknown>;
}

/**
 * Reiht den Start samt geplanter Sätze ein und gibt das Training zurück, das
 * die Seite bis zum Nachtragen zeigt. Wirft, wenn keine Übungen bekannt sind:
 * ein leeres Training ließe sich offline nicht füllen, weil der Katalog dann
 * ebenfalls fehlt.
 */
export function offlineStarten(start: OfflineStart): Workout {
  if (start.uebungen.length === 0) {
    throw new Error('Ohne Netz lässt sich nur der Vorschlag für heute starten.');
  }
  const workoutId = naechsteErsatznummer();
  const jetzt = new Date().toISOString();
  einreihen({
    method: 'POST',
    path: '/workouts',
    body: {
      plan_day_id: start.plan_day_id ?? null,
      name: start.name,
      uebungen: start.uebungen,
      prefill: false,
      ...(start.bereitschaft ?? {}),
    },
    ersatzId: workoutId,
  });

  const saetze: WorkoutSet[] = [];
  const vorgaben: PlanTarget[] = [];
  for (const u of start.uebungen) {
    const name = start.namen[u.exercise_id] ?? '';
    for (let nummer = 1; nummer <= Math.max(1, u.saetze); nummer++) {
      const satzId = naechsteErsatznummer();
      const rumpf = {
        exercise_id: u.exercise_id,
        set_number: nummer,
        weight_kg: u.gewicht_kg,
        reps: u.wdh,
        set_type: 'normal',
        is_warmup: false,
        is_completed: false,
      };
      einreihen({ method: 'POST', path: `/workouts/${workoutId}/sets`, body: rumpf, ersatzId: satzId });
      saetze.push({
        ...rumpf,
        id: satzId,
        exercise_name: name,
        duration_seconds: null,
        distance_meters: null,
        rpe: null,
        group_id: null,
        notes: null,
        completed_at: null,
      });
    }
    vorgaben.push({
      exercise_id: u.exercise_id,
      exercise_name: name,
      target_sets: u.saetze,
      target_reps_min: u.wdh ?? 1,
      target_reps_max: u.wdh ?? 1,
      target_rpe: null,
      rest_seconds: start.pausen?.[u.exercise_id] ?? 90,
      notes: null,
    });
  }

  const b = start.bereitschaft ?? {};
  const w: Workout = {
    id: workoutId,
    plan_day_id: start.plan_day_id ?? null,
    plan_day_name: null,
    name: start.name ?? 'Training',
    started_at: jetzt,
    finished_at: null,
    notes: null,
    rating: null,
    fatigue_level: (b.fatigue_level as number | null) ?? null,
    sleep_quality: (b.sleep_quality as number | null) ?? null,
    motivation: (b.motivation as number | null) ?? null,
    pre_notes: (b.pre_notes as string | null) ?? null,
    sets: saetze,
    plan_targets: vorgaben,
  };
  lokalSpeichern(w);
  return w;
}

/** Namen und Pausen je Übung aus der Auskunft, für `offlineStarten`. */
export function namenAus(jetzt: TrainingJetzt | null | undefined): {
  namen: Record<number, string>; pausen: Record<number, number>;
} {
  const namen: Record<number, string> = {};
  const pausen: Record<number, number> = {};
  for (const u of jetzt?.uebungen ?? []) {
    namen[u.exercise_id] = u.name;
    pausen[u.exercise_id] = u.pause_s;
  }
  return { namen, pausen };
}
