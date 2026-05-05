// Service Worker — AI Engineering Design DB
// Cache-first for static assets, network-first for dynamic data

const CACHE_NAME = "ai-eng-db-v1";

// Static assets to pre-cache on install
const STATIC_ASSETS = [
  "/browse",
  "/browse.html",
  "/explorer.css",
  "/manifest.json",
];

// ── Install: pre-cache static assets ──────────────────────────────
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) =>
      cache.addAll(STATIC_ASSETS).catch(() => {
        // Silently ignore failures (e.g. when served from file://)
      })
    )
  );
  self.skipWaiting();
});

// ── Activate: clean up old caches ─────────────────────────────────
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// ── Fetch: routing strategy ────────────────────────────────────────
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests and non-http(s) protocols
  if (event.request.method !== "GET") return;
  if (!url.protocol.startsWith("http")) return;

  // Network-first for graph-data.json (changes frequently)
  if (url.pathname.includes("graph-data.json")) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          // Cache the fresh response
          const toCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, toCache));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Cache-first for all other GET requests
  event.respondWith(
    caches.match(event.request).then(
      (cached) => cached || fetch(event.request).then((response) => {
        // Cache successful responses (not API calls, not opaque)
        if (
          response.ok &&
          !url.pathname.startsWith("/api/") &&
          response.type !== "opaque"
        ) {
          const toCache = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, toCache));
        }
        return response;
      })
    )
  );
});
