/**
 * Service Worker.
 *
 * Zwei Dinge waren vorher nicht in Ordnung:
 *
 * 1. Vorgeladen wurden nur "/" und das Manifest. Die eigentlichen Programm-
 *    und Stildateien liegen unter /assets/ mit Namen, die bei jedem Bau neu
 *    gewuerfelt werden. Offline startete die App deshalb nur dann, wenn genau
 *    diese Dateien vorher zufaellig schon einmal geladen worden waren.
 * 2. Die Startseite wurde aus dem Zwischenspeicher zuerst bedient. Nach einem
 *    Ausrollen sah man die alte Fassung, bis man ein zweites Mal lud.
 *
 * Jetzt: beim Einrichten die Startseite holen, die darin genannten Dateien
 * mitnehmen (die Liste steht in der Datei, sie muss nicht gepflegt werden),
 * Navigationsanfragen aus dem Netz mit Rueckfall auf den Zwischenspeicher,
 * die gehashten Dateien aus dem Zwischenspeicher.
 */
const CACHE_NAME = 'fitness-v2';
const SHELL = ['/', '/manifest.json'];

async function shellVorladen(cache) {
  await cache.addAll(SHELL);
  try {
    const antwort = await cache.match('/') || await fetch('/');
    const text = await antwort.clone().text();
    // src="/assets/index-a1b2c3.js" und href="/assets/index-d4e5f6.css"
    const dateien = [...text.matchAll(/(?:src|href)="(\/[^"]+\.(?:js|css|woff2?|png|svg))"/g)]
      .map(treffer => treffer[1]);
    await Promise.all(dateien.map(pfad => cache.add(pfad).catch(() => {})));
  } catch {
    // Ohne Netz beim Einrichten bleibt es bei der Shell. Beim naechsten
    // Aufruf mit Netz wird nachgeholt.
  }
}

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(shellVorladen).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const { request } = e;
  const url = new URL(request.url);

  if (request.method !== 'GET') return;

  // Fachliche Aufrufe niemals zwischenspeichern. Veraltete Trainingsdaten
  // waeren schlimmer als eine Fehlermeldung; fuer das Schreiben offline gibt
  // es die Warteschlange in der App (src/warteschlange.ts).
  if (url.pathname.startsWith('/api')) return;

  // Die Seite selbst: frisch, wenn moeglich, sonst aus dem Speicher. So wirkt
  // ein Ausrollen sofort und die App startet trotzdem ohne Netz.
  if (request.mode === 'navigate') {
    e.respondWith(
      fetch(request)
        .then((antwort) => {
          const kopie = antwort.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put('/', kopie));
          return antwort;
        })
        .catch(() => caches.match('/'))
    );
    return;
  }

  // Dateien mit Bau-Kennung im Namen aendern sich nie: aus dem Speicher, und
  // nur bei Fehlschlag aus dem Netz.
  e.respondWith(
    caches.match(request).then((gespeichert) => {
      if (gespeichert) return gespeichert;
      return fetch(request).then((antwort) => {
        if (antwort.ok) {
          const kopie = antwort.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, kopie));
        }
        return antwort;
      });
    })
  );
});
