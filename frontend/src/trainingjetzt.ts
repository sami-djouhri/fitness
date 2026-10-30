/**
 * Die Antwort auf "was trainiere ich jetzt", einmal für alle Oberflächen.
 *
 * Die Frage hatte am 2026-10-24 vier Antworten im Haus: den Dienst
 * ``/api/training/jetzt``, den Nachbau auf der Startseite, die nirgends
 * eingebundene ``TodayTraining.tsx`` und die Schnellwahl auf der
 * Trainingsseite, die sich die frischeste Körperregion aus
 * ``/progress/muscle-freshness`` suchte. Die ersten drei sind erledigt, diese
 * Datei trägt den Rest: Startseite und Trainingsseite zeigen dieselbe Liste
 * und starten dieselbe Einheit, weil sie dieselben zwei Funktionen benutzen.
 *
 * Die Schnellwahl war dabei nicht nur eine zweite Meinung, sondern eine
 * leere: sie legte eine Sitzung mit einem Namen an ("Rücken Training") und
 * ohne eine einzige Übung.
 */

import type { JetztUebung, TrainingJetzt } from './types';

/**
 * Das Ziel einer Übung in einer Zeile: Sätze, Wiederholungen, Gewicht.
 *
 * Drei Fälle, die vor dem 2026-10-24 alle gleich aussahen, nämlich als
 * "3 x 8" ohne Zahl: ein gemessenes Gewicht, ein geschätztes und eine echte
 * Lücke. Die Tilde unterscheidet das Geschätzte, das Fragezeichen die Lücke.
 * Eine Übung ohne Gewichtsbedarf (Klimmzüge, Liegestütze) bleibt ohne Zusatz,
 * denn dort ist nichts offen.
 */
export function ziel(u: JetztUebung): string {
  const kopf = `${u.saetze} x ${u.wdh ?? '?'}`;
  if (u.gewicht_kg != null) {
    const tilde = u.gewicht_quelle === 'geschaetzt' ? '~' : '';
    return `${kopf} @ ${tilde}${u.gewicht_kg.toLocaleString('de')} kg`;
  }
  if (u.gewicht_quelle === 'fehlt') return `${kopf} @ ? kg`;
  return kopf;
}

/**
 * Was beim Start mitgegeben wird: genau diese Liste, mit diesen Sätzen.
 *
 * ``pendingPlanDayId`` geht mit, auch wenn die Übungen vom Plantag
 * abweichen. An ihr hängt die Rotation zum nächsten Plantag; ohne sie bliebe
 * der Plan für immer beim selben Tag stehen. Dass die Liste trotzdem gilt,
 * stellt das Backend sicher (``uebungen`` schlägt ``plan_day_id``).
 */
export function startzustand(jetzt: TrainingJetzt) {
  return {
    pendingName: jetzt.titel,
    pendingPlanDayId: jetzt.plantag_id ?? undefined,
    pendingUebungen: jetzt.uebungen.map((u) => ({
      exercise_id: u.exercise_id,
      saetze: u.saetze,
      wdh: u.wdh,
      gewicht_kg: u.gewicht_kg,
    })),
  };
}
