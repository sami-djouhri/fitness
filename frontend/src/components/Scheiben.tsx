/* Der Scheibenstapel: das Kennzeichen dieser App.
 *
 * Ein Gewicht steht hier nicht nur als Zahl da, sondern als das, was man
 * tatsaechlich auf die Stange steckt. 100 kg sind eine Zahl; zwei rote und
 * eine gruene Scheibe je Seite sind eine Handlung.
 *
 * Die Farben sind nicht erfunden, sie sind genormt (IWF): 25 rot, 20 blau,
 * 15 gelb, 10 gruen, 5 weiss, 2,5 und 1,25 dunkel. Wer im Kraftraum steht,
 * liest sie ohne Legende, und genau deshalb sind sie in dieser App die
 * einzige Buntfarbe neben der Frische-Skala.
 *
 * Gezeigt wird eine Seite der Stange, denn so laedt man auch: symmetrisch.
 */

interface Props {
  /** Gesamtgewicht inklusive Stange, in Kilogramm. */
  kg: number | null | undefined;
  /** Gewicht der Stange. 20 kg ist die Wettkampfstange. */
  stange?: number;
  /** Ohne Beschriftung, nur die Scheiben. Fuer enge Zeilen. */
  knapp?: boolean;
}

/* Von schwer nach leicht, denn so wird geladen. */
const SCHEIBEN: { kg: number; marke: string }[] = [
  { kg: 25, marke: 'scheibe-25' },
  { kg: 20, marke: 'scheibe-20' },
  { kg: 15, marke: 'scheibe-15' },
  { kg: 10, marke: 'scheibe-10' },
  { kg: 5, marke: 'scheibe-5' },
  { kg: 2.5, marke: 'scheibe-2' },
  { kg: 1.25, marke: 'scheibe-2' },
];

/* Welche Scheiben auf EINE Seite kommen.
   Gerechnet wird in Gramm, weil 2.5 und 1.25 als Fliesskomma sonst Reste
   hinterlassen, die als Phantomscheibe auftauchen. */
export function ladung(kg: number, stange: number): { kg: number; marke: string }[] {
  const jeSeiteGramm = Math.round(((kg - stange) / 2) * 1000);
  if (jeSeiteGramm <= 0) return [];

  const stapel: { kg: number; marke: string }[] = [];
  let rest = jeSeiteGramm;
  for (const s of SCHEIBEN) {
    const gramm = Math.round(s.kg * 1000);
    while (rest >= gramm) {
      stapel.push(s);
      rest -= gramm;
    }
  }
  return stapel;
}

export default function Scheiben({ kg, stange = 20, knapp }: Props) {
  if (kg == null || kg <= stange) return null;

  const stapel = ladung(kg, stange);
  if (stapel.length === 0) return null;

  /* Geht die Last nicht glatt auf, steht das da, statt sie stillschweigend
     zu runden: eine Ladung, die nicht stimmt, ist schlimmer als keine. */
  const gezeigt = stapel.reduce((s, p) => s + p.kg, 0) * 2 + stange;
  const exakt = Math.abs(gezeigt - kg) < 0.01;

  const text = stapel.map((p) => (p.kg % 1 === 0 ? p.kg : p.kg.toFixed(2))).join(' + ');

  return (
    <span
      className={`scheiben${knapp ? ' knapp' : ''}`}
      title={`Je Seite: ${text} kg auf ${stange} kg Stange`}
      aria-label={`Ladung je Seite: ${text} Kilogramm auf einer ${stange} Kilogramm Stange`}
    >
      {stapel.map((p, i) => (
        <span
          key={i}
          className="scheibe"
          style={{
            background: `var(--${p.marke})`,
            height: `${Math.min(100, 46 + p.kg * 2.2)}%`,
          }}
        />
      ))}
      {!knapp && <span className="scheiben-text">je Seite</span>}
      {!exakt && <span className="scheiben-rest" title="Geht mit Normscheiben nicht glatt auf">~</span>}
    </span>
  );
}
