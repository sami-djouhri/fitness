/**
 * Die Uebungen als Bewegung, nach Muster statt nach Uebung.
 *
 * ★★ Der Grund fuer diese Aufteilung: eine eigene Keyframe-Spur je Uebung
 * waeren bei 167 Uebungen 167 Spuren, und die letzten fuenfzig bekaemen nie
 * eine. Animiert wird deshalb das **Bewegungsmuster**, das jede Uebung im
 * Katalog traegt (``muster`` in app/data/uebungskatalog.py). 22 Muster decken
 * den ganzen Katalog ab, und eine neue Uebung ist damit ohne Zeichenarbeit
 * vorgefuehrt.
 *
 * Eine Bewegung ist ein Paar aus zwei Stellungen. Dazwischen wird
 * interpoliert und wieder zurueck. Die Rotationen stehen in Grad, weil man
 * sie so von Hand nachbessern kann, ohne zu rechnen.
 */

import type { KnochenId } from './skelett';

export type Pose = Partial<Record<KnochenId, [number, number, number]>>;

export interface Bewegung {
  /** Ausgangsstellung, meist die gestreckte Position. */
  start: Pose;
  /** Endstellung, meist die gebeugte. */
  ende: Pose;
  /** Millisekunden fuer einen Weg. Hin und zurueck ist das Doppelte. */
  dauer: number;
  /** Wie die Figur dabei steht. Verschiebt die ganze Wurzel. */
  lage?: 'stehend' | 'liegend_rueck' | 'liegend_bauch' | 'haengend' | 'sitzend' | 'stuetz';
  /** Kurzbeschreibung, steht unter der Vorfuehrung. */
  hinweis: string;
}

const NEUTRAL_ARME: Pose = {
  oberarm_l: [0, 0, -8],
  oberarm_r: [0, 0, 8],
};

export const BEWEGUNGEN: Record<string, Bewegung> = {
  // ------------------------------------------------------------- Druecken
  druecken_horizontal: {
    lage: 'liegend_rueck',
    dauer: 1100,
    hinweis: 'Absenken bis die Brust gedehnt ist, dann wegdrücken.',
    start: {
      oberarm_l: [0, 0, -78], oberarm_r: [0, 0, 78],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
    },
    ende: {
      oberarm_l: [0, 0, -58], oberarm_r: [0, 0, 58],
      unterarm_l: [0, 0, -74], unterarm_r: [0, 0, 74],
      brustkorb: [4, 0, 0],
    },
  },
  druecken_schraeg: {
    lage: 'liegend_rueck',
    dauer: 1100,
    hinweis: 'Wie horizontales Drücken, nur schräg nach oben.',
    start: {
      oberarm_l: [-22, 0, -74], oberarm_r: [-22, 0, 74],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
    },
    ende: {
      oberarm_l: [-14, 0, -56], oberarm_r: [-14, 0, 56],
      unterarm_l: [0, 0, -70], unterarm_r: [0, 0, 70],
    },
  },
  druecken_vertikal: {
    lage: 'stehend',
    dauer: 1100,
    hinweis: 'Von Ohrhöhe gerade nach oben, Rippen unten lassen.',
    start: {
      oberarm_l: [0, 0, -96], oberarm_r: [0, 0, 96],
      unterarm_l: [0, 0, -92], unterarm_r: [0, 0, 92],
    },
    ende: {
      oberarm_l: [0, 0, -166], oberarm_r: [0, 0, 166],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
    },
  },
  dip: {
    lage: 'stuetz',
    dauer: 1200,
    hinweis: 'Bis die Oberarme waagerecht sind, nicht tiefer.',
    start: {
      oberarm_l: [4, 0, -6], oberarm_r: [4, 0, 6],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
      brustkorb: [6, 0, 0],
    },
    ende: {
      oberarm_l: [-28, 0, -6], oberarm_r: [-28, 0, 6],
      unterarm_l: [0, 0, -86], unterarm_r: [0, 0, 86],
      brustkorb: [14, 0, 0],
    },
  },

  // ---------------------------------------------------------------- Ziehen
  ziehen_vertikal: {
    lage: 'haengend',
    dauer: 1300,
    hinweis: 'Schulterblätter zuerst nach unten, dann die Arme beugen.',
    start: {
      oberarm_l: [0, 0, -168], oberarm_r: [0, 0, 168],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
      brustkorb: [0, 0, 0],
    },
    ende: {
      oberarm_l: [0, 0, -128], oberarm_r: [0, 0, 128],
      unterarm_l: [0, 0, -122], unterarm_r: [0, 0, 122],
      brustkorb: [-8, 0, 0],
    },
  },
  ziehen_horizontal: {
    lage: 'stehend',
    dauer: 1200,
    hinweis: 'Ellenbogen zur Hüfte führen, Schulterblätter zusammen.',
    start: {
      brustkorb: [36, 0, 0],
      oberarm_l: [-34, 0, -6], oberarm_r: [-34, 0, 6],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
    },
    ende: {
      brustkorb: [34, 0, 0],
      oberarm_l: [22, 0, -8], oberarm_r: [22, 0, 8],
      unterarm_l: [0, 0, -96], unterarm_r: [0, 0, 96],
    },
  },

  // ----------------------------------------------------------------- Beine
  beugen_knie: {
    lage: 'stehend',
    dauer: 1400,
    hinweis: 'Knie folgen den Zehen, so tief wie die Beweglichkeit erlaubt.',
    start: {
      oberschenkel_l: [0, 0, 0], oberschenkel_r: [0, 0, 0],
      unterschenkel_l: [0, 0, 0], unterschenkel_r: [0, 0, 0],
      becken: [0, 0, 0], brustkorb: [0, 0, 0],
      ...NEUTRAL_ARME,
    },
    ende: {
      oberschenkel_l: [-88, 0, -6], oberschenkel_r: [-88, 0, 6],
      unterschenkel_l: [96, 0, 0], unterschenkel_r: [96, 0, 0],
      fuss_l: [-24, 0, 0], fuss_r: [-24, 0, 0],
      becken: [24, 0, 0], brustkorb: [8, 0, 0],
      oberarm_l: [-72, 0, -10], oberarm_r: [-72, 0, 10],
    },
  },
  ausfallschritt: {
    lage: 'stehend',
    dauer: 1400,
    hinweis: 'Ein Bein vor, das hintere Knie sinkt zum Boden.',
    start: {
      oberschenkel_l: [0, 0, 0], oberschenkel_r: [0, 0, 0],
      unterschenkel_l: [0, 0, 0], unterschenkel_r: [0, 0, 0],
      ...NEUTRAL_ARME,
    },
    ende: {
      oberschenkel_l: [-72, 0, 0], unterschenkel_l: [78, 0, 0],
      oberschenkel_r: [26, 0, 0], unterschenkel_r: [96, 0, 0],
      becken: [8, 0, 0],
    },
  },
  hueftstreckung: {
    lage: 'stehend',
    dauer: 1300,
    hinweis: 'Hüfte nach hinten schieben, Knie fast gestreckt lassen.',
    start: {
      becken: [0, 0, 0], brustkorb: [0, 0, 0],
      oberarm_l: [0, 0, -4], oberarm_r: [0, 0, 4],
    },
    ende: {
      becken: [66, 0, 0], brustkorb: [-6, 0, 0],
      oberschenkel_l: [-8, 0, 0], oberschenkel_r: [-8, 0, 0],
      unterschenkel_l: [14, 0, 0], unterschenkel_r: [14, 0, 0],
      oberarm_l: [-62, 0, -4], oberarm_r: [-62, 0, 4],
    },
  },
  wade: {
    lage: 'stehend',
    dauer: 900,
    hinweis: 'Ferse tief absenken, dann ganz nach oben.',
    start: { fuss_l: [16, 0, 0], fuss_r: [16, 0, 0], ...NEUTRAL_ARME },
    ende: {
      fuss_l: [-34, 0, 0], fuss_r: [-34, 0, 0],
      becken: [0, 0, 0],
      ...NEUTRAL_ARME,
    },
  },

  // ------------------------------------------------------------------ Arme
  armbeugen: {
    lage: 'stehend',
    dauer: 1000,
    hinweis: 'Ellenbogen bleiben am Körper, nur der Unterarm bewegt sich.',
    start: {
      oberarm_l: [0, 0, -6], oberarm_r: [0, 0, 6],
      unterarm_l: [0, 0, 0], unterarm_r: [0, 0, 0],
    },
    ende: {
      oberarm_l: [-8, 0, -6], oberarm_r: [-8, 0, 6],
      unterarm_l: [0, 0, -132], unterarm_r: [0, 0, 132],
    },
  },
  armstrecken: {
    lage: 'stehend',
    dauer: 1000,
    hinweis: 'Oberarm steht still, der Unterarm streckt sich.',
    start: {
      oberarm_l: [0, 0, -164], oberarm_r: [0, 0, 164],
      unterarm_l: [0, 0, -140], unterarm_r: [0, 0, 140],
    },
    ende: {
      oberarm_l: [0, 0, -166], oberarm_r: [0, 0, 166],
      unterarm_l: [0, 0, -6], unterarm_r: [0, 0, 6],
    },
  },
  seitheben: {
    lage: 'stehend',
    dauer: 1100,
    hinweis: 'Bis Schulterhöhe, kein Schwung.',
    start: { oberarm_l: [0, 0, -6], oberarm_r: [0, 0, 6] },
    ende: {
      oberarm_l: [0, 0, -88], oberarm_r: [0, 0, 88],
      unterarm_l: [0, 0, -8], unterarm_r: [0, 0, 8],
    },
  },
  frontheben: {
    lage: 'stehend',
    dauer: 1100,
    hinweis: 'Gerade nach vorne bis Schulterhöhe.',
    start: { oberarm_l: [0, 0, -6], oberarm_r: [0, 0, 6] },
    ende: { oberarm_l: [-86, 0, -6], oberarm_r: [-86, 0, 6] },
  },
  fliegende: {
    lage: 'liegend_rueck',
    dauer: 1300,
    hinweis: 'Im Bogen öffnen und schließen, Ellenbogen leicht gebeugt.',
    start: {
      oberarm_l: [0, 0, -80], oberarm_r: [0, 0, 80],
      unterarm_l: [0, 0, -14], unterarm_r: [0, 0, 14],
    },
    ende: {
      oberarm_l: [0, 0, -6], oberarm_r: [0, 0, 6],
      unterarm_l: [0, 0, -14], unterarm_r: [0, 0, 14],
    },
  },
  reverse_fly: {
    lage: 'stehend',
    dauer: 1200,
    hinweis: 'Vorgebeugt zur Seite öffnen, Schulterblätter zusammen.',
    start: {
      brustkorb: [56, 0, 0],
      oberarm_l: [-52, 0, -6], oberarm_r: [-52, 0, 6],
    },
    ende: {
      brustkorb: [56, 0, 0],
      oberarm_l: [-46, 0, -84], oberarm_r: [-46, 0, 84],
    },
  },

  // ----------------------------------------------------------------- Rumpf
  rumpfbeugen: {
    lage: 'liegend_rueck',
    dauer: 1000,
    hinweis: 'Nur die Schultern lösen sich, der untere Rücken bleibt liegen.',
    start: { brustkorb: [0, 0, 0], hals: [0, 0, 0] },
    ende: { brustkorb: [-34, 0, 0], hals: [-12, 0, 0] },
  },
  beinheben: {
    lage: 'liegend_rueck',
    dauer: 1200,
    hinweis: 'Becken einrollen, nicht nur die Hüfte beugen.',
    start: {
      oberschenkel_l: [0, 0, 0], oberschenkel_r: [0, 0, 0],
      becken: [0, 0, 0],
    },
    ende: {
      oberschenkel_l: [-88, 0, 0], oberschenkel_r: [-88, 0, 0],
      becken: [-22, 0, 0],
    },
  },
  rotation: {
    lage: 'stehend',
    dauer: 1300,
    hinweis: 'Aus dem Rumpf drehen, die Hüfte bleibt ruhig.',
    start: {
      brustkorb: [0, -34, 0],
      oberarm_l: [-72, 0, -10], oberarm_r: [-72, 0, 10],
    },
    ende: {
      brustkorb: [0, 34, 0],
      oberarm_l: [-72, 0, -10], oberarm_r: [-72, 0, 10],
    },
  },
  halten: {
    lage: 'stuetz',
    dauer: 2200,
    hinweis: 'Position halten, Körper bleibt eine Linie.',
    start: { brustkorb: [0, 0, 0], becken: [0, 0, 0] },
    ende: { brustkorb: [1.5, 0, 0], becken: [-1.5, 0, 0] },
  },

  // --------------------------------------------------------------- Sonstige
  cardio: {
    lage: 'stehend',
    dauer: 500,
    hinweis: 'Gleichmäßiges Tempo über die ganze Dauer.',
    start: {
      oberschenkel_l: [-52, 0, 0], unterschenkel_l: [42, 0, 0],
      oberschenkel_r: [16, 0, 0], unterschenkel_r: [26, 0, 0],
      oberarm_l: [34, 0, -8], oberarm_r: [-34, 0, 8],
      unterarm_l: [0, 0, -76], unterarm_r: [0, 0, 76],
    },
    ende: {
      oberschenkel_l: [16, 0, 0], unterschenkel_l: [26, 0, 0],
      oberschenkel_r: [-52, 0, 0], unterschenkel_r: [42, 0, 0],
      oberarm_l: [-34, 0, -8], oberarm_r: [34, 0, 8],
      unterarm_l: [0, 0, -76], unterarm_r: [0, 0, 76],
    },
  },
  dehnen: {
    lage: 'stehend',
    dauer: 2600,
    hinweis: 'In die Dehnung gehen und dort ruhig atmen.',
    start: {
      brustkorb: [0, 0, 0],
      oberarm_l: [0, 0, -10], oberarm_r: [0, 0, 10],
    },
    ende: {
      brustkorb: [0, 0, -16],
      oberarm_l: [0, 0, -158], oberarm_r: [0, 0, 24],
      unterarm_l: [0, 0, -34], unterarm_r: [0, 0, 10],
    },
  },
};

/** Lage der Figur im Raum, je Ausgangsstellung. */
export const LAGEN: Record<string, { drehung: [number, number, number]; hoehe: number }> = {
  stehend: { drehung: [0, 0, 0], hoehe: 0 },
  liegend_rueck: { drehung: [-90, 0, 0], hoehe: -8.4 },
  liegend_bauch: { drehung: [90, 0, 0], hoehe: -8.4 },
  haengend: { drehung: [0, 0, 0], hoehe: 0 },
  sitzend: { drehung: [0, 0, 0], hoehe: -1.6 },
  stuetz: { drehung: [-72, 0, 0], hoehe: -6.2 },
};

export function bewegungFuer(muster: string | null | undefined): Bewegung | null {
  if (!muster) return null;
  return BEWEGUNGEN[muster] ?? null;
}
