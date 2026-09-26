/**
 * Das Knochengeruest der Figur.
 *
 * Warum eigene Geometrie statt eines fertigen Anatomie-Modells
 * ------------------------------------------------------------
 * Die freien Anatomiedatensaetze (BodyParts3D, Z-Anatomy) sind CC BY-SA und
 * bringen rund 2,3 Millionen Dreiecke bei etwa 33 MB mit. Auf einem Handy
 * laedt das nicht, und die Share-Alike-Pflicht am Asset waere fuer ein
 * Projekt, das veroeffentlicht werden soll, eine zusaetzliche Auflage. Diese
 * Figur wird stattdessen im Code erzeugt: unter 100 kB, keine Lizenzfrage,
 * anatomisch stilisiert statt fotorealistisch.
 *
 * Aufbau
 * ------
 * Eine Hierarchie von ``THREE.Group``. Jeder Knochen sitzt relativ zu seinem
 * Elternteil, Muskeln haengen als starre Meshes daran. Kein Skinning:
 * ★ Bei einer Low-Poly-Figur faellt der Unterschied kaum auf, und Skinning
 * haette fuer jeden der 44 Muskeln Gewichte je Vertex gebraucht, also genau
 * die Handarbeit, die man bei zweihundert Uebungen nicht zu Ende bringt.
 *
 * Masse in Dezimetern, Figur rund 18 Einheiten hoch, Fuesse auf y = 0.
 */

import * as THREE from 'three';

export type KnochenId =
  | 'becken' | 'lende' | 'brustkorb' | 'hals' | 'kopf'
  | 'schulter_l' | 'oberarm_l' | 'unterarm_l' | 'hand_l'
  | 'schulter_r' | 'oberarm_r' | 'unterarm_r' | 'hand_r'
  | 'oberschenkel_l' | 'unterschenkel_l' | 'fuss_l'
  | 'oberschenkel_r' | 'unterschenkel_r' | 'fuss_r';

interface Knochendefinition {
  id: KnochenId;
  eltern: KnochenId | null;
  /** Position relativ zum Elternteil, in der Neutralstellung. */
  position: [number, number, number];
}

/**
 * ★ Reihenfolge ist wichtig: ein Knochen wird an sein Elternteil gehaengt,
 * das muss vorher existieren. Ein spaeter einsortierter Eintrag laesst den
 * Ast still am Ursprung liegen, statt einen Fehler zu werfen.
 */
export const KNOCHEN: Knochendefinition[] = [
  { id: 'becken', eltern: null, position: [0, 9.4, 0] },
  { id: 'lende', eltern: 'becken', position: [0, 1.0, 0] },
  { id: 'brustkorb', eltern: 'lende', position: [0, 1.9, 0] },
  { id: 'hals', eltern: 'brustkorb', position: [0, 1.9, 0] },
  { id: 'kopf', eltern: 'hals', position: [0, 0.9, 0] },

  { id: 'schulter_l', eltern: 'brustkorb', position: [1.05, 1.55, 0] },
  { id: 'oberarm_l', eltern: 'schulter_l', position: [0.75, -0.25, 0] },
  { id: 'unterarm_l', eltern: 'oberarm_l', position: [0, -2.7, 0] },
  { id: 'hand_l', eltern: 'unterarm_l', position: [0, -2.5, 0] },

  { id: 'schulter_r', eltern: 'brustkorb', position: [-1.05, 1.55, 0] },
  { id: 'oberarm_r', eltern: 'schulter_r', position: [-0.75, -0.25, 0] },
  { id: 'unterarm_r', eltern: 'oberarm_r', position: [0, -2.7, 0] },
  { id: 'hand_r', eltern: 'unterarm_r', position: [0, -2.5, 0] },

  { id: 'oberschenkel_l', eltern: 'becken', position: [0.78, -0.7, 0] },
  { id: 'unterschenkel_l', eltern: 'oberschenkel_l', position: [0, -4.1, 0] },
  { id: 'fuss_l', eltern: 'unterschenkel_l', position: [0, -3.9, 0] },

  { id: 'oberschenkel_r', eltern: 'becken', position: [-0.78, -0.7, 0] },
  { id: 'unterschenkel_r', eltern: 'oberschenkel_r', position: [0, -4.1, 0] },
  { id: 'fuss_r', eltern: 'unterschenkel_r', position: [0, -3.9, 0] },
];

export type Skelett = Record<KnochenId, THREE.Group>;

export function skelettBauen(wurzel: THREE.Object3D): Skelett {
  const knochen = {} as Skelett;
  for (const def of KNOCHEN) {
    const gruppe = new THREE.Group();
    gruppe.name = def.id;
    gruppe.position.set(...def.position);
    if (def.eltern) {
      knochen[def.eltern].add(gruppe);
    } else {
      wurzel.add(gruppe);
    }
    knochen[def.id] = gruppe;
  }
  return knochen;
}

/** Alle Knochen in die Neutralstellung zuruecksetzen. */
export function neutral(skelett: Skelett): void {
  for (const def of KNOCHEN) {
    skelett[def.id].rotation.set(0, 0, 0);
    skelett[def.id].position.set(...def.position);
  }
}
