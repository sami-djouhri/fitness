/**
 * Zahlen deutsch schreiben: 72,5 kg statt 72.5 kg. `toFixed` setzt immer
 * einen Punkt, und daneben stehen Zahlen aus `toLocaleString` mit Komma.
 */
export function dez(wert: number, stellen = 1): string {
  return wert.toLocaleString('de-DE', { minimumFractionDigits: stellen, maximumFractionDigits: stellen });
}

/** Wie `dez`, aber ohne erzwungene Nachkommastellen (72,5 und 70). */
export function zahl(wert: number): string {
  return wert.toLocaleString('de-DE', { maximumFractionDigits: 2 });
}
