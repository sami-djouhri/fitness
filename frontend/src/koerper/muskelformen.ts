/**
 * Wo jeder der 44 Muskeln sitzt, wie gross er ist und woran er haengt.
 *
 * Die Kennungen sind dieselben wie in ``app/services/muskulatur.py``. ★ Das
 * ist die einzige Stelle, an der beide Seiten uebereinstimmen muessen, und
 * ``test_koerpermodell`` prueft es gegen die Registry aus dem Backend: ein
 * Tippfehler hier faerbt einen Muskel nie ein, und im Code sieht man ihm das
 * nicht an.
 *
 * ``form`` bestimmt die Geometrie:
 *   spindel  Ellipsoid, an beiden Enden verjuengt (Bizeps, Waden, Quadrizeps)
 *   platte   flach gedrueckt (Brust, Latissimus, Bauch)
 *   keil     zu einem Ende hin schmaler (Trapez, Rueckenstrecker)
 *   rund     annaehernd kugelig (Schultern, Gesaess)
 *
 * ``seite`` ist 'l', 'r' oder 'm' (mittig, nur einmal vorhanden). Alles mit
 * 'l' oder 'r' wird gespiegelt zweimal erzeugt, damit die Definitionen nicht
 * doppelt gepflegt werden muessen.
 */

import type { KnochenId } from './skelett';

export type Form = 'spindel' | 'platte' | 'keil' | 'rund';

export interface Muskelform {
  /** Kennung aus services/muskulatur.py. */
  id: string;
  knochen: KnochenId | 'becken' | 'brustkorb';
  form: Form;
  /** Position relativ zum Knochen. */
  pos: [number, number, number];
  /** Halbachsen des Ellipsoids. */
  groesse: [number, number, number];
  /** Drehung in Grad um x, y, z. */
  drehung?: [number, number, number];
  seite: 'l' | 'r' | 'm';
  /** Tiefenschicht: hoehere Werte liegen weiter aussen und verdecken. */
  schicht?: number;
}

/**
 * Die Definitionen fuer die linke Koerperhaelfte und die Mitte. Die rechte
 * entsteht durch Spiegeln in ``muskelformenAlle``.
 */
const HALB: Muskelform[] = [
  // ---------------------------------------------------------------- Brust
  { id: 'brust_oben', knochen: 'brustkorb', form: 'platte', seite: 'l',
    pos: [0.62, 1.02, 0.72], groesse: [0.62, 0.34, 0.30], drehung: [0, 0, -14] },
  { id: 'brust_mitte', knochen: 'brustkorb', form: 'platte', seite: 'l',
    pos: [0.66, 0.42, 0.76], groesse: [0.70, 0.44, 0.34] },
  { id: 'brust_unten', knochen: 'brustkorb', form: 'platte', seite: 'l',
    pos: [0.62, -0.16, 0.72], groesse: [0.62, 0.30, 0.30], drehung: [0, 0, 10] },
  { id: 'serratus', knochen: 'brustkorb', form: 'keil', seite: 'l',
    pos: [1.02, -0.20, 0.30], groesse: [0.26, 0.52, 0.44], drehung: [0, 0, 18] },

  // ------------------------------------------------------------ Schultern
  { id: 'delta_vorne', knochen: 'schulter_l', form: 'rund', seite: 'l',
    pos: [0.34, -0.06, 0.42], groesse: [0.40, 0.46, 0.32], schicht: 2 },
  { id: 'delta_seite', knochen: 'schulter_l', form: 'rund', seite: 'l',
    pos: [0.60, 0.02, 0.0], groesse: [0.34, 0.50, 0.46], schicht: 2 },
  { id: 'delta_hinten', knochen: 'schulter_l', form: 'rund', seite: 'l',
    pos: [0.34, -0.06, -0.42], groesse: [0.40, 0.44, 0.32], schicht: 2 },
  { id: 'rotatorenmanschette', knochen: 'schulter_l', form: 'platte', seite: 'l',
    pos: [0.16, -0.30, -0.46], groesse: [0.34, 0.28, 0.18] },

  // -------------------------------------------------------------- Ruecken
  { id: 'latissimus', knochen: 'brustkorb', form: 'keil', seite: 'l',
    pos: [0.72, -0.30, -0.62], groesse: [0.60, 1.10, 0.34], drehung: [0, 0, -8] },
  { id: 'teres_major', knochen: 'brustkorb', form: 'spindel', seite: 'l',
    pos: [0.86, 0.92, -0.52], groesse: [0.36, 0.22, 0.22], drehung: [0, 0, -34] },
  { id: 'rhomboiden', knochen: 'brustkorb', form: 'platte', seite: 'l',
    pos: [0.36, 0.72, -0.72], groesse: [0.38, 0.52, 0.16] },
  { id: 'trapez_mitte', knochen: 'brustkorb', form: 'platte', seite: 'l',
    pos: [0.60, 1.06, -0.66], groesse: [0.52, 0.32, 0.20] },
  { id: 'trapez_oben', knochen: 'hals', form: 'keil', seite: 'l',
    pos: [0.52, -0.36, -0.24], groesse: [0.62, 0.30, 0.34], drehung: [0, 0, 22] },
  { id: 'trapez_unten', knochen: 'lende', form: 'keil', seite: 'l',
    pos: [0.30, 1.30, -0.62], groesse: [0.30, 0.62, 0.16], drehung: [0, 0, -6] },
  { id: 'nacken', knochen: 'hals', form: 'spindel', seite: 'l',
    pos: [0.24, 0.10, -0.14], groesse: [0.18, 0.42, 0.20] },

  // ----------------------------------------------------------------- Arme
  { id: 'bizeps_lang', knochen: 'oberarm_l', form: 'spindel', seite: 'l',
    pos: [0.20, -1.28, 0.24], groesse: [0.20, 0.86, 0.22], schicht: 2 },
  { id: 'bizeps_kurz', knochen: 'oberarm_l', form: 'spindel', seite: 'l',
    pos: [-0.14, -1.30, 0.22], groesse: [0.18, 0.82, 0.20], schicht: 2 },
  { id: 'brachialis', knochen: 'oberarm_l', form: 'spindel', seite: 'l',
    pos: [0.16, -2.10, 0.14], groesse: [0.20, 0.44, 0.18] },
  { id: 'trizeps_lang', knochen: 'oberarm_l', form: 'spindel', seite: 'l',
    pos: [-0.10, -1.20, -0.26], groesse: [0.20, 0.94, 0.22], schicht: 2 },
  { id: 'trizeps_lateral', knochen: 'oberarm_l', form: 'spindel', seite: 'l',
    pos: [0.26, -1.10, -0.20], groesse: [0.19, 0.80, 0.22], schicht: 2 },
  { id: 'trizeps_medial', knochen: 'oberarm_l', form: 'spindel', seite: 'l',
    pos: [0.02, -2.06, -0.20], groesse: [0.22, 0.42, 0.20] },
  { id: 'brachioradialis', knochen: 'unterarm_l', form: 'spindel', seite: 'l',
    pos: [0.20, -0.72, 0.16], groesse: [0.17, 0.72, 0.18], schicht: 2 },
  { id: 'unterarm_beuger', knochen: 'unterarm_l', form: 'spindel', seite: 'l',
    pos: [-0.02, -1.10, 0.20], groesse: [0.22, 0.98, 0.20] },
  { id: 'unterarm_strecker', knochen: 'unterarm_l', form: 'spindel', seite: 'l',
    pos: [0.06, -1.10, -0.20], groesse: [0.22, 0.98, 0.20] },

  // ---------------------------------------------------------------- Rumpf
  { id: 'bauch_oben', knochen: 'lende', form: 'platte', seite: 'm',
    pos: [0, 0.98, 0.60], groesse: [0.50, 0.44, 0.22] },
  { id: 'bauch_unten', knochen: 'lende', form: 'platte', seite: 'm',
    pos: [0, 0.12, 0.58], groesse: [0.46, 0.50, 0.22] },
  { id: 'obliquus_extern', knochen: 'lende', form: 'keil', seite: 'l',
    pos: [0.66, 0.50, 0.36], groesse: [0.26, 0.78, 0.36], drehung: [0, 0, 8], schicht: 2 },
  { id: 'obliquus_intern', knochen: 'lende', form: 'keil', seite: 'l',
    pos: [0.62, 0.16, 0.30], groesse: [0.20, 0.50, 0.30] },
  { id: 'transversus', knochen: 'lende', form: 'platte', seite: 'm',
    pos: [0, 0.46, 0.32], groesse: [0.66, 0.80, 0.24] },
  { id: 'erector_spinae', knochen: 'lende', form: 'keil', seite: 'l',
    pos: [0.26, 0.60, -0.52], groesse: [0.26, 1.10, 0.24] },
  { id: 'quadratus_lumborum', knochen: 'lende', form: 'platte', seite: 'l',
    pos: [0.52, 0.10, -0.40], groesse: [0.22, 0.44, 0.22] },

  // ---------------------------------------------------------------- Beine
  { id: 'gluteus_maximus', knochen: 'becken', form: 'rund', seite: 'l',
    pos: [0.52, -0.30, -0.56], groesse: [0.62, 0.62, 0.44], schicht: 2 },
  { id: 'gluteus_medius', knochen: 'becken', form: 'rund', seite: 'l',
    pos: [0.82, 0.16, -0.20], groesse: [0.36, 0.44, 0.36] },
  { id: 'rectus_femoris', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [0.02, -1.90, 0.44], groesse: [0.30, 1.60, 0.24], schicht: 2 },
  { id: 'vastus_lateralis', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [0.46, -1.80, 0.14], groesse: [0.28, 1.62, 0.36], schicht: 2 },
  { id: 'vastus_medialis', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [-0.34, -2.60, 0.30], groesse: [0.26, 0.86, 0.30], schicht: 2 },
  { id: 'vastus_intermedius', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [0.04, -2.00, 0.16], groesse: [0.32, 1.40, 0.26] },
  { id: 'adduktoren', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [-0.38, -1.60, 0.02], groesse: [0.26, 1.44, 0.32] },
  { id: 'hueftbeuger', knochen: 'becken', form: 'spindel', seite: 'l',
    pos: [0.40, -0.26, 0.42], groesse: [0.22, 0.52, 0.24] },
  { id: 'biceps_femoris', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [0.34, -1.90, -0.40], groesse: [0.28, 1.60, 0.28], schicht: 2 },
  { id: 'semitendinosus', knochen: 'oberschenkel_l', form: 'spindel', seite: 'l',
    pos: [-0.24, -1.90, -0.40], groesse: [0.26, 1.58, 0.26], schicht: 2 },
  { id: 'gastrocnemius', knochen: 'unterschenkel_l', form: 'spindel', seite: 'l',
    pos: [0.02, -1.28, -0.32], groesse: [0.34, 1.16, 0.30], schicht: 2 },
  { id: 'soleus', knochen: 'unterschenkel_l', form: 'spindel', seite: 'l',
    pos: [0.02, -2.36, -0.24], groesse: [0.28, 0.80, 0.26] },

  // Ausdauer ist kein Muskel. Wird im Modell nicht dargestellt, steht aber
  // in der Registry, damit Cardio-Uebungen eine Zuordnung haben.
];

/**
 * Alle Muskeln, linke Seite plus gespiegelte rechte.
 *
 * ★ Die Spiegelung dreht x und die Drehungen um y und z mit. Ohne das
 * schauen die Keile auf der rechten Seite in die falsche Richtung, was man
 * erst am gerenderten Bild sieht und im Code fuer richtig haelt.
 */
export function muskelformenAlle(): Muskelform[] {
  const alle: Muskelform[] = [];
  for (const m of HALB) {
    if (m.seite === 'm') {
      alle.push(m);
      continue;
    }
    alle.push({ ...m, knochen: m.knochen });
    const [rx, ry, rz] = m.drehung ?? [0, 0, 0];
    alle.push({
      ...m,
      seite: 'r',
      knochen: m.knochen.endsWith('_l')
        ? (m.knochen.replace(/_l$/, '_r') as KnochenId)
        : m.knochen,
      pos: [-m.pos[0], m.pos[1], m.pos[2]],
      drehung: [rx, -ry, -rz],
    });
  }
  return alle;
}

/** Kennungen, die im Modell dargestellt werden. Fuer die Gegenprobe. */
export function dargestellteMuskeln(): Set<string> {
  return new Set(HALB.map((m) => m.id));
}

/**
 * Koerperteile ohne Muskelzuordnung: Kopf, Haende, Fuesse, Rumpfkern.
 * Sie machen die Figur erkennbar und sind nicht anklickbar.
 */
export interface Fuellform {
  knochen: KnochenId;
  pos: [number, number, number];
  groesse: [number, number, number];
  form: Form;
}

/**
 * ★ Nach der ersten visuellen Prüfung vergrößert. Im ersten Wurf waren die
 * Füllkörper schmaler als die Muskeln, die darauf sitzen: die Figur las sich
 * als Traube grüner Blasen ohne erkennbare Silhouette. Ein Körper wird von
 * seinem Umriss getragen, die Muskeln liegen darauf.
 */
export const FUELLFORMEN: Fuellform[] = [
  { knochen: 'kopf', pos: [0, 0.66, 0.04], groesse: [0.72, 0.88, 0.76], form: 'rund' },
  { knochen: 'hals', pos: [0, 0.24, -0.02], groesse: [0.38, 0.52, 0.38], form: 'spindel' },
  { knochen: 'brustkorb', pos: [0, 0.52, 0], groesse: [1.14, 1.40, 0.70], form: 'rund' },
  { knochen: 'lende', pos: [0, 0.46, 0], groesse: [0.86, 1.10, 0.58], form: 'spindel' },
  { knochen: 'becken', pos: [0, -0.22, 0], groesse: [1.02, 0.82, 0.66], form: 'rund' },
  { knochen: 'oberarm_l', pos: [0, -1.35, 0], groesse: [0.32, 1.48, 0.32], form: 'spindel' },
  { knochen: 'oberarm_r', pos: [0, -1.35, 0], groesse: [0.32, 1.48, 0.32], form: 'spindel' },
  { knochen: 'unterarm_l', pos: [0, -1.22, 0], groesse: [0.27, 1.32, 0.27], form: 'spindel' },
  { knochen: 'unterarm_r', pos: [0, -1.22, 0], groesse: [0.27, 1.32, 0.27], form: 'spindel' },
  { knochen: 'hand_l', pos: [0, -0.36, 0], groesse: [0.24, 0.46, 0.14], form: 'platte' },
  { knochen: 'hand_r', pos: [0, -0.36, 0], groesse: [0.24, 0.46, 0.14], form: 'platte' },
  { knochen: 'oberschenkel_l', pos: [0, -2.05, 0], groesse: [0.46, 2.15, 0.46], form: 'spindel' },
  { knochen: 'oberschenkel_r', pos: [0, -2.05, 0], groesse: [0.46, 2.15, 0.46], form: 'spindel' },
  { knochen: 'unterschenkel_l', pos: [0, -1.90, 0], groesse: [0.35, 2.00, 0.35], form: 'spindel' },
  { knochen: 'unterschenkel_r', pos: [0, -1.90, 0], groesse: [0.35, 2.00, 0.35], form: 'spindel' },
  { knochen: 'fuss_l', pos: [0, -0.32, 0.28], groesse: [0.28, 0.22, 0.66], form: 'platte' },
  { knochen: 'fuss_r', pos: [0, -0.32, 0.28], groesse: [0.28, 0.22, 0.66], form: 'platte' },
];

/**
 * Ruhestellung: Arme leicht vom Körper weg, sonst stecken die Oberarm-Muskeln
 * im Rumpf und man sieht weder Latissimus noch Trizeps.
 */
export const RUHESTELLUNG: Record<string, [number, number, number]> = {
  oberarm_l: [0, 0, -9],
  oberarm_r: [0, 0, 9],
  oberschenkel_l: [0, 0, -2],
  oberschenkel_r: [0, 0, 2],
};
