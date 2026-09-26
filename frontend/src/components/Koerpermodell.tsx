import { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { skelettBauen, neutral, type Skelett, type KnochenId } from '../koerper/skelett';
import {
  muskelformenAlle, FUELLFORMEN, RUHESTELLUNG, type Form, type Muskelform,
} from '../koerper/muskelformen';
import { bewegungFuer, LAGEN, type Pose } from '../koerper/bewegungen';

/**
 * Der Körper in 3D: drehbar, zoombar, jeder Muskel einzeln anwählbar.
 *
 * Löst die SVG-Karte ab, die zwei feste Ansichten kannte und in der jeder
 * angetippte Oberschenkelmuskel auf die Region `quads` fiel. Hier trägt jedes
 * Mesh seine eigene Muskelkennung, und die ist dieselbe wie im Backend.
 *
 * Zwei Einfärbungen:
 *   `frische`    wie lange der Muskel Ruhe hatte (Zustandsansicht)
 *   `abdeckung`  was die gerade gewählten Übungen treffen würden
 *
 * ★ Die zweite ist der eigentliche Grund für das Modell: beim Ab- und
 * Anwählen von Übungen sieht man sofort, ob mehr oder weniger Partien
 * drankommen. Vorher war das eine Liste, aus der man es sich denken musste.
 */

export type Faerbung = 'frische' | 'abdeckung';

interface Props {
  /** Muskelkennung auf einen Wert zwischen 0 und 1. */
  werte: Record<string, number>;
  faerbung: Faerbung;
  ausgewaehlt?: string | null;
  /** Muskeln, die hervorgehoben werden, ohne angewählt zu sein. */
  hervorgehoben?: string[];
  onMuskelKlick?: (muskelId: string) => void;
  /** Bewegungsmuster aus dem Katalog. Ist es gesetzt, führt die Figur es vor. */
  muster?: string | null;
  hoehe?: number;
  /** Beschriftung unter dem Modell, etwa der Name des Muskels. */
  fusszeile?: string;
}

/* ------------------------------------------------------------------ */
/*  Farben                                                             */
/* ------------------------------------------------------------------ */

const GRUNDFARBE = new THREE.Color('#39414f');
const FUELLFARBE = new THREE.Color('#2b313c');

/** Frische: rot heißt lange her, grün heißt frisch trainiert. */
const SKALA_FRISCHE = [
  { wert: 0.0, farbe: new THREE.Color('#ef4444') },
  { wert: 0.35, farbe: new THREE.Color('#f97316') },
  { wert: 0.6, farbe: new THREE.Color('#facc15') },
  { wert: 0.8, farbe: new THREE.Color('#4ade80') },
  { wert: 1.0, farbe: new THREE.Color('#22c55e') },
];

/** Abdeckung: von grau (kommt nicht dran) nach blau (wird voll getroffen). */
const SKALA_ABDECKUNG = [
  { wert: 0.0, farbe: new THREE.Color('#39414f') },
  { wert: 0.3, farbe: new THREE.Color('#1e4d7b') },
  { wert: 0.6, farbe: new THREE.Color('#2b7fd4') },
  { wert: 1.0, farbe: new THREE.Color('#5eb2ff') },
];

function ausSkala(skala: typeof SKALA_FRISCHE, wert: number): THREE.Color {
  const w = Math.max(0, Math.min(1, wert));
  for (let i = 1; i < skala.length; i++) {
    if (w <= skala[i].wert) {
      const a = skala[i - 1];
      const b = skala[i];
      const t = (w - a.wert) / (b.wert - a.wert || 1);
      return a.farbe.clone().lerp(b.farbe, t);
    }
  }
  return skala[skala.length - 1].farbe.clone();
}

/* ------------------------------------------------------------------ */
/*  Geometrie                                                          */
/* ------------------------------------------------------------------ */

/**
 * Eine Grundkugel für alle Muskeln, je Form einmal verzerrt.
 *
 * ★ Vier Geometrien für 90 Meshes statt 90 eigener: das ist der Unterschied
 * zwischen flüssig und ruckelig auf einem Telefon. Die Verzerrung steckt in
 * der Geometrie, nicht in der Skalierung des Meshes, weil `scale` sonst auch
 * die Normalen verzieht und die Beleuchtung flackert.
 */
function geometrieFuer(form: Form): THREE.BufferGeometry {
  const g = new THREE.SphereGeometry(1, 10, 7);
  const pos = g.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    if (form === 'spindel') {
      // An den Enden schlanker: ein Muskelbauch, kein Ei.
      const f = 1 - 0.22 * y * y;
      pos.setXYZ(i, x * f, y, z * f);
    } else if (form === 'platte') {
      pos.setXYZ(i, x, y, z * 0.55);
    } else if (form === 'keil') {
      // Zum oberen Ende hin schmaler: Trapez, Latissimus, Rückenstrecker.
      const f = 0.42 + 0.58 * (1 - (y + 1) / 2);
      pos.setXYZ(i, x * f, y, z * f);
    }
  }
  g.computeVertexNormals();
  return g;
}

const GRAD = Math.PI / 180;

/* ------------------------------------------------------------------ */
/*  Kameraabstand                                                      */
/* ------------------------------------------------------------------ */

/**
 * ★★ Ausgerechnet statt geraten. Beim ersten Versuch stand hier 26, dann 20,
 * und beide waren falsch: bei 26 wirkte die Figur verloren, bei 20 waren Kopf
 * und Füße abgeschnitten. Beides sieht man erst im gerenderten Bild, und
 * beides lässt sich rechnen.
 *
 * Die Figur reicht von etwa y = -8.8 (Fußsohle) bis y = +7.4 (Scheitel),
 * gemessen an der Knochenkette in skelett.ts plus den Füllformen. Das sind
 * 16.2 Einheiten um eine Mitte bei -0.7. Bei senkrechtem Öffnungswinkel
 * FOV gilt: sichtbare Höhe = 2 * Abstand * tan(FOV / 2).
 *
 * Nach 18.6 sichtbaren Einheiten aufgelöst bleibt die Figur mit etwas Luft
 * im Bild, ohne im Rahmen zu schwimmen.
 */
const FOV = 32;
const FIGUR_MITTE_Y = -0.7;
const FIGUR_HOEHE = 16.2;
const LUFT = 1.06;
const STANDARDABSTAND = Math.round(
  (FIGUR_HOEHE * LUFT) / (2 * Math.tan((FOV / 2) * GRAD)),
);

function ruhestellung(skelett: Skelett): void {
  for (const [id, grad] of Object.entries(RUHESTELLUNG)) {
    const knochen = skelett[id as KnochenId];
    if (knochen) {
      knochen.rotation.set(grad[0] * GRAD, grad[1] * GRAD, grad[2] * GRAD);
    }
  }
}

function poseAnwenden(skelett: Skelett, a: Pose, b: Pose, t: number): void {
  const ids = new Set([...Object.keys(a), ...Object.keys(b)]) as Set<KnochenId>;
  for (const id of ids) {
    const von = a[id] ?? [0, 0, 0];
    const nach = b[id] ?? [0, 0, 0];
    const knochen = skelett[id];
    if (!knochen) continue;
    knochen.rotation.set(
      (von[0] + (nach[0] - von[0]) * t) * GRAD,
      (von[1] + (nach[1] - von[1]) * t) * GRAD,
      (von[2] + (nach[2] - von[2]) * t) * GRAD,
    );
  }
}

/* ------------------------------------------------------------------ */
/*  Komponente                                                         */
/* ------------------------------------------------------------------ */

export default function Koerpermodell({
  werte, faerbung, ausgewaehlt, hervorgehoben, onMuskelKlick,
  muster, hoehe = 420, fusszeile,
}: Props) {
  const behaelterRef = useRef<HTMLDivElement>(null);
  const [ueberfahren, setUeberfahren] = useState<string | null>(null);
  const [fehler, setFehler] = useState<string | null>(null);

  // Alles, was zwischen den Renderdurchläufen bestehen bleibt. In einem Ref,
  // damit ein Neuzeichnen von React die Szene nicht neu aufbaut.
  const szene = useRef<{
    renderer: THREE.WebGLRenderer;
    scene: THREE.Scene;
    kamera: THREE.PerspectiveCamera;
    skelett: Skelett;
    wurzel: THREE.Group;
    muskeln: Map<string, THREE.Mesh[]>;
    anklickbar: THREE.Mesh[];
    aufraeumen: () => void;
  } | null>(null);

  const zustand = useRef({
    drehungY: 0, drehungX: 0.05, abstand: STANDARDABSTAND,
    zeigerUnten: false, letzteX: 0, letzteY: 0, bewegt: 0,
    startAbstand: 0,
  });

  /* --- Aufbau, einmalig --- */
  useEffect(() => {
    const behaelter = behaelterRef.current;
    if (!behaelter) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      // ★ Ohne WebGL keine leere Fläche, sondern eine Ansage. Ein schwarzes
      // Rechteck sieht wie ein Ladefehler aus, und man sucht ihn im Netz.
      setFehler('Dieses Gerät zeigt kein 3D. Die Muskelauswahl geht über die Liste darunter.');
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(behaelter.clientWidth, hoehe);
    behaelter.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const kamera = new THREE.PerspectiveCamera(
      FOV, behaelter.clientWidth / hoehe, 0.5, 200);

    scene.add(new THREE.AmbientLight(0xffffff, 0.62));
    const licht = new THREE.DirectionalLight(0xffffff, 0.85);
    licht.position.set(6, 14, 12);
    scene.add(licht);
    const gegenlicht = new THREE.DirectionalLight(0x93b8ff, 0.28);
    gegenlicht.position.set(-8, 6, -10);
    scene.add(gegenlicht);

    const wurzel = new THREE.Group();
    // Die Figur so verschieben, dass ihre Mitte im Ursprung liegt: sonst
    // dreht sie sich um die Füße statt um sich selbst.
    const traeger = new THREE.Group();
    traeger.add(wurzel);
    wurzel.position.y = -9.2;
    scene.add(traeger);

    const skelett = skelettBauen(wurzel);

    const geometrien: Record<Form, THREE.BufferGeometry> = {
      spindel: geometrieFuer('spindel'),
      platte: geometrieFuer('platte'),
      keil: geometrieFuer('keil'),
      rund: geometrieFuer('rund'),
    };

    // ★ Deckend statt durchscheinend: mit Transparenz verschwand der
    // Rumpf hinter den Muskeln, und die Figur las sich als Traube grüner
    // Blasen statt als Körper. Die Silhouette muss der Füllkörper tragen.
    const fuellmaterial = new THREE.MeshLambertMaterial({ color: FUELLFARBE });
    for (const f of FUELLFORMEN) {
      const mesh = new THREE.Mesh(geometrien[f.form], fuellmaterial);
      mesh.position.set(...f.pos);
      mesh.scale.set(...f.groesse);
      mesh.userData.fuellung = true;
      skelett[f.knochen].add(mesh);
    }

    const muskeln = new Map<string, THREE.Mesh[]>();
    const anklickbar: THREE.Mesh[] = [];
    for (const m of muskelformenAlle() as Muskelform[]) {
      const material = new THREE.MeshLambertMaterial({ color: GRUNDFARBE });
      const mesh = new THREE.Mesh(geometrien[m.form], material);
      mesh.position.set(...m.pos);
      mesh.scale.set(...m.groesse);
      if (m.drehung) {
        mesh.rotation.set(m.drehung[0] * GRAD, m.drehung[1] * GRAD, m.drehung[2] * GRAD);
      }
      mesh.renderOrder = m.schicht ?? 1;
      mesh.userData.muskel = m.id;
      const knochen = skelett[m.knochen as KnochenId];
      if (!knochen) continue;
      knochen.add(mesh);
      const liste = muskeln.get(m.id) ?? [];
      liste.push(mesh);
      muskeln.set(m.id, liste);
      anklickbar.push(mesh);
    }

    let laeuft = true;
    let rahmen = 0;
    const uhrStart = performance.now();

    const zeichnen = () => {
      if (!laeuft) return;
      rahmen = requestAnimationFrame(zeichnen);
      const z = zustand.current;

      // Kamera auf einer Kugel um die Figur.
      const phi = z.drehungY;
      const theta = Math.max(-1.1, Math.min(1.1, z.drehungX));
      kamera.position.set(
        z.abstand * Math.cos(theta) * Math.sin(phi),
        FIGUR_MITTE_Y + z.abstand * Math.sin(theta),
        z.abstand * Math.cos(theta) * Math.cos(phi),
      );
      // Auf die Mitte der Figur schauen, nicht auf den Ursprung: sonst sitzt
      // sie außermittig im Rahmen und wird an einem Ende abgeschnitten.
      kamera.lookAt(0, FIGUR_MITTE_Y, 0);

      // Bewegung, falls ein Muster gesetzt ist.
      const bew = bewegungFuer(musterRef.current);
      if (bew) {
        const t = ((performance.now() - uhrStart) % (bew.dauer * 2)) / bew.dauer;
        const fortschritt = t <= 1 ? t : 2 - t;
        // Weich ein- und ausschwingen, damit es nicht mechanisch wirkt.
        const weich = fortschritt * fortschritt * (3 - 2 * fortschritt);
        neutral(skelett);
        poseAnwenden(skelett, bew.start, bew.ende, weich);
        const lage = LAGEN[bew.lage ?? 'stehend'];
        traeger.rotation.x = lage.drehung[0] * GRAD;
        wurzel.position.y = -9.2 + lage.hoehe;
      } else {
        neutral(skelett);
        ruhestellung(skelett);
        traeger.rotation.x = 0;
        wurzel.position.y = -9.2;
      }

      renderer.render(scene, kamera);
    };
    zeichnen();

    const beiGroesse = () => {
      if (!behaelter.clientWidth) return;
      renderer.setSize(behaelter.clientWidth, hoehe);
      kamera.aspect = behaelter.clientWidth / hoehe;
      kamera.updateProjectionMatrix();
    };
    window.addEventListener('resize', beiGroesse);

    szene.current = {
      renderer, scene, kamera, skelett, wurzel, muskeln, anklickbar,
      aufraeumen: () => {
        laeuft = false;
        cancelAnimationFrame(rahmen);
        window.removeEventListener('resize', beiGroesse);
        for (const g of Object.values(geometrien)) g.dispose();
        for (const liste of muskeln.values()) {
          for (const mesh of liste) (mesh.material as THREE.Material).dispose();
        }
        fuellmaterial.dispose();
        renderer.dispose();
        if (renderer.domElement.parentNode === behaelter) {
          behaelter.removeChild(renderer.domElement);
        }
      },
    };

    return () => {
      szene.current?.aufraeumen();
      szene.current = null;
    };
    // Nur beim ersten Aufbau. Die Höhe ändert sich zur Laufzeit nicht.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Das aktuelle Muster in einem Ref, damit die Zeichenschleife es liest,
  // ohne dass die Szene bei jeder Änderung neu entsteht.
  const musterRef = useRef<string | null | undefined>(muster);
  useEffect(() => { musterRef.current = muster; }, [muster]);

  /* --- Einfärben --- */
  useEffect(() => {
    const s = szene.current;
    if (!s) return;
    const skala = faerbung === 'frische' ? SKALA_FRISCHE : SKALA_ABDECKUNG;
    const hervor = new Set(hervorgehoben ?? []);

    for (const [id, meshes] of s.muskeln) {
      const wert = werte[id];
      let farbe: THREE.Color;
      if (wert === undefined || wert === null) {
        farbe = GRUNDFARBE.clone();
      } else {
        farbe = ausSkala(skala, wert);
      }
      const istAusgewaehlt = ausgewaehlt === id;
      const istHervor = hervor.has(id);
      for (const mesh of meshes) {
        const mat = mesh.material as THREE.MeshLambertMaterial;
        mat.color.copy(farbe);
        if (istAusgewaehlt) {
          mat.emissive = new THREE.Color('#60a5fa');
          mat.emissiveIntensity = 0.55;
        } else if (istHervor) {
          mat.emissive = new THREE.Color('#2b7fd4');
          mat.emissiveIntensity = 0.3;
        } else if (ueberfahren === id) {
          mat.emissive = new THREE.Color('#ffffff');
          mat.emissiveIntensity = 0.22;
        } else {
          mat.emissive = new THREE.Color('#000000');
          mat.emissiveIntensity = 0;
        }
        mat.needsUpdate = true;
      }
    }
  }, [werte, faerbung, ausgewaehlt, hervorgehoben, ueberfahren]);

  /* --- Steuerung --- */
  const treffer = useCallback((ev: React.PointerEvent): string | null => {
    const s = szene.current;
    if (!s) return null;
    const rechteck = (ev.currentTarget as HTMLElement).getBoundingClientRect();
    const zeiger = new THREE.Vector2(
      ((ev.clientX - rechteck.left) / rechteck.width) * 2 - 1,
      -((ev.clientY - rechteck.top) / rechteck.height) * 2 + 1,
    );
    const strahl = new THREE.Raycaster();
    strahl.setFromCamera(zeiger, s.kamera);
    const schnitte = strahl.intersectObjects(s.anklickbar, false);
    return schnitte.length > 0 ? (schnitte[0].object.userData.muskel as string) : null;
  }, []);

  const beiZeigerRunter = (ev: React.PointerEvent) => {
    const z = zustand.current;
    z.zeigerUnten = true;
    z.letzteX = ev.clientX;
    z.letzteY = ev.clientY;
    z.bewegt = 0;
    (ev.currentTarget as HTMLElement).setPointerCapture(ev.pointerId);
  };

  const beiZeigerBewegung = (ev: React.PointerEvent) => {
    const z = zustand.current;
    if (z.zeigerUnten) {
      const dx = ev.clientX - z.letzteX;
      const dy = ev.clientY - z.letzteY;
      z.bewegt += Math.abs(dx) + Math.abs(dy);
      z.drehungY -= dx * 0.008;
      z.drehungX += dy * 0.006;
      z.letzteX = ev.clientX;
      z.letzteY = ev.clientY;
      return;
    }
    // Nur auf Zeigergeräten überfahren: auf dem Touchscreen gibt es kein
    // Schweben, und ein hängengebliebener Hover-Zustand verwirrt.
    if (ev.pointerType === 'mouse') setUeberfahren(treffer(ev));
  };

  const beiZeigerHoch = (ev: React.PointerEvent) => {
    const z = zustand.current;
    z.zeigerUnten = false;
    // Unter zehn Pixel Bewegung war es ein Antippen, kein Drehen.
    if (z.bewegt < 10) {
      const id = treffer(ev);
      if (id && onMuskelKlick) onMuskelKlick(id);
    }
  };

  const beiRad = (ev: React.WheelEvent) => {
    const z = zustand.current;
    z.abstand = Math.max(12, Math.min(60, z.abstand + ev.deltaY * 0.03));
  };

  // Zwei Finger zum Zoomen.
  const beruehrungen = useRef<Map<number, { x: number; y: number }>>(new Map());
  const beiBeruehrung = (ev: React.TouchEvent) => {
    if (ev.touches.length !== 2) return;
    const [a, b] = [ev.touches[0], ev.touches[1]];
    const abstand = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
    const z = zustand.current;
    if (ev.type === 'touchstart') {
      z.startAbstand = abstand;
      return;
    }
    if (z.startAbstand > 0) {
      const faktor = z.startAbstand / abstand;
      z.abstand = Math.max(12, Math.min(60, z.abstand * (1 + (faktor - 1) * 0.25)));
      z.startAbstand = abstand;
    }
  };

  if (fehler) {
    return <div className="modell-fehler">{fehler}</div>;
  }

  return (
    <div className="koerpermodell">
      <div
        ref={behaelterRef}
        className="koerpermodell-buehne"
        style={{ height: hoehe, touchAction: 'none' }}
        onPointerDown={beiZeigerRunter}
        onPointerMove={beiZeigerBewegung}
        onPointerUp={beiZeigerHoch}
        onPointerLeave={() => { zustand.current.zeigerUnten = false; setUeberfahren(null); }}
        onWheel={beiRad}
        onTouchStart={beiBeruehrung}
        onTouchMove={beiBeruehrung}
        onTouchEnd={() => { zustand.current.startAbstand = 0; beruehrungen.current.clear(); }}
      />
      <div className="koerpermodell-hilfe">
        <span>Ziehen zum Drehen, zwei Finger zum Zoomen</span>
        <button
          type="button"
          className="modell-knopf"
          onClick={() => {
            zustand.current.drehungY = 0;
            zustand.current.drehungX = 0.05;
            zustand.current.abstand = STANDARDABSTAND;
          }}
        >
          Ansicht zurücksetzen
        </button>
        <button
          type="button"
          className="modell-knopf"
          onClick={() => { zustand.current.drehungY += Math.PI; }}
        >
          Umdrehen
        </button>
      </div>
      {fusszeile && <div className="koerpermodell-fuss">{fusszeile}</div>}
    </div>
  );
}
