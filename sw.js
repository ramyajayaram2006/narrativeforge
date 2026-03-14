/**
 * NarrativeForge Service Worker
 * Provides offline support for the app shell and cached assets.
 * Strategy: Cache-first for static assets, network-first for API calls.
 */

const CACHE_NAME = 'narrativeforge-v1';
const OFFLINE_URL = '/offline.html';

// Assets to pre-cache on install
const PRECACHE_ASSETS = [
  '/',
  '/static/css/main.css',
  '/static/js/main.js',
];

// ── Install ────────────────────────────────────────────────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      // Cache what we can, ignore failures (Streamlit dynamically generates)
      return Promise.allSettled(
        PRECACHE_ASSETS.map(url => cache.add(url).catch(() => {}))
      );
    }).then(() => self.skipWaiting())
  );
});

// ── Activate ────────────────────────────────────────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames =>
      Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME)
          .map(name => caches.delete(name))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch ────────────────────────────────────────────────────────────────
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET, cross-origin, and Streamlit WebSocket/SSE requests
  if (request.method !== 'GET') return;
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/_stcore/')) return;
  if (url.pathname.startsWith('/stream')) return;

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/') ||
      url.pathname.startsWith('/component/')) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, clone));
          }
          return response;
        }).catch(() => new Response('Offline', { status: 503 }));
      })
    );
    return;
  }

  // Everything else: network-first with offline fallback
  event.respondWith(
    fetch(request).catch(() => {
      return caches.match(request).then(cached => {
        if (cached) return cached;
        // For navigation requests, show offline message
        if (request.mode === 'navigate') {
          return new Response(
            `<!DOCTYPE html><html><head><meta charset=utf-8>
            <title>NarrativeForge — Offline</title>
            <style>body{background:#0D0E14;color:#C5C8D4;font-family:Inter,sans-serif;
            display:flex;align-items:center;justify-content:center;min-height:100vh;
            flex-direction:column;gap:16px;text-align:center;}
            h1{color:#4D6BFE;font-size:2rem;}p{color:#6B7080;max-width:400px;}</style>
            </head><body>
            <h1>◆ NarrativeForge</h1>
            <p>You're offline. Your story data is saved locally — reconnect to sync.</p>
            <p style="font-size:0.8rem;color:#4D6BFE;">Your drafts are safe.</p>
            </body></html>`,
            { headers: { 'Content-Type': 'text/html' } }
          );
        }
        return new Response('Offline', { status: 503 });
      });
    })
  );
});

// ── Background sync for draft saves ────────────────────────────────────────
self.addEventListener('sync', event => {
  if (event.tag === 'sync-drafts') {
    event.waitUntil(
      // Notify all clients that sync is available
      self.clients.matchAll().then(clients =>
        clients.forEach(client =>
          client.postMessage({ type: 'SYNC_READY' })
        )
      )
    );
  }
});

// ── Push notifications (writing streak reminders) ──────────────────────────
self.addEventListener('push', event => {
  if (!event.data) return;
  const data = event.data.json().catch(() => ({ title: 'NarrativeForge', body: 'Time to write!' }));
  event.waitUntil(
    self.registration.showNotification(data.title || 'NarrativeForge', {
      body: data.body || 'Your story is waiting.',
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: 'narrativeforge-reminder',
      data: { url: '/' },
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow(event.notification.data?.url || '/')
  );
});
