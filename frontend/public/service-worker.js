/* eslint-disable no-restricted-globals */

// Service Worker per SNALS Mail PWA
// Versione: 1.0.0

const CACHE_NAME = 'snals-mail-v1';
const RUNTIME_CACHE = 'snals-mail-runtime-v1';
const API_CACHE = 'snals-mail-api-v1';

// File statici da cachare immediatamente
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/offline.html', // Pagina offline fallback
];

// Pattern API da cachare con strategia Network First
const API_PATTERNS = [
  /\/api\/emails/,
  /\/api\/calendario/,
  /\/api\/interpelli/,
  /\/api\/schools/,
  /\/api\/settings/,
];

// Pattern da NON cachare (sempre network)
const NO_CACHE_PATTERNS = [
  /\/api\/emails\/fetch/,
  /\/api\/.*\/reprocess/,
  /\/api\/.*\/execute/,
];

// ============ INSTALL EVENT ============
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker v1.0.0...');

  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((error) => {
        console.error('[SW] Failed to cache static assets:', error);
      });
    }).then(() => {
      console.log('[SW] Installation complete');
      return self.skipWaiting(); // Attiva immediatamente
    })
  );
});

// ============ ACTIVATE EVENT ============
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');

  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          // Rimuovi cache vecchie
          if (cacheName !== CACHE_NAME &&
              cacheName !== RUNTIME_CACHE &&
              cacheName !== API_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Activation complete');
      return self.clients.claim(); // Prendi controllo immediatamente
    })
  );
});

// ============ FETCH EVENT ============
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignora richieste non-HTTP
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Strategia per API
  if (url.pathname.startsWith('/api')) {
    // NON cachare operazioni di scrittura/modifica
    if (NO_CACHE_PATTERNS.some(pattern => pattern.test(url.pathname))) {
      event.respondWith(fetch(request));
      return;
    }

    // Strategia Network First per API
    if (API_PATTERNS.some(pattern => pattern.test(url.pathname))) {
      event.respondWith(networkFirstStrategy(request, API_CACHE));
      return;
    }

    // Default: solo network per altre API
    event.respondWith(fetch(request));
    return;
  }

  // Strategia Cache First per asset statici
  event.respondWith(cacheFirstStrategy(request));
});

// ============ PUSH NOTIFICATIONS ============
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');

  let notificationData = {
    title: 'SNALS Mail',
    body: 'Nuova notifica',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/badge-72x72.png',
    tag: 'snals-notification',
    requireInteraction: false,
  };

  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = {
        ...notificationData,
        title: data.title || notificationData.title,
        body: data.body || notificationData.body,
        icon: data.icon || notificationData.icon,
        tag: data.tag || notificationData.tag,
        data: data.data || {},
        actions: data.actions || [],
      };
    } catch (error) {
      console.error('[SW] Error parsing push data:', error);
    }
  }

  event.waitUntil(
    self.registration.showNotification(notificationData.title, notificationData)
  );
});

// ============ NOTIFICATION CLICK ============
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event.notification.tag);

  event.notification.close();

  // Apri/focalizza l'app
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Cerca una finestra già aperta
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i];
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus();
        }
      }

      // Apri nuova finestra
      if (clients.openWindow) {
        const targetUrl = event.notification.data?.url || '/';
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// ============ BACKGROUND SYNC ============
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync triggered:', event.tag);

  if (event.tag === 'sync-emails') {
    event.waitUntil(syncEmails());
  }
});

// ============ PERIODIC SYNC ============
self.addEventListener('periodicsync', (event) => {
  console.log('[SW] Periodic sync triggered:', event.tag);

  if (event.tag === 'fetch-new-emails') {
    event.waitUntil(fetchNewEmails());
  }
});

// ============ CACHE STRATEGIES ============

/**
 * Network First Strategy
 * Prova prima la rete, poi fallback alla cache
 */
async function networkFirstStrategy(request, cacheName) {
  try {
    const networkResponse = await fetch(request);

    // Copia la risposta (le response sono single-use)
    const responseToCache = networkResponse.clone();

    // Salva in cache solo le risposte OK
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, responseToCache);
    }

    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);

    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // Se neanche la cache ha la risposta, restituisci errore offline
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'Nessuna connessione disponibile e nessun dato in cache'
      }),
      {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Cache First Strategy
 * Prova prima la cache, poi la rete
 */
async function cacheFirstStrategy(request) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);

    // Salva in cache runtime
    const cache = await caches.open(RUNTIME_CACHE);
    cache.put(request, networkResponse.clone());

    return networkResponse;
  } catch (error) {
    console.error('[SW] Fetch failed:', error);

    // Fallback per navigazione: pagina offline
    if (request.mode === 'navigate') {
      const offlinePage = await caches.match('/offline.html');
      if (offlinePage) {
        return offlinePage;
      }
    }

    throw error;
  }
}

// ============ BACKGROUND TASKS ============

async function syncEmails() {
  console.log('[SW] Syncing emails...');

  try {
    const response = await fetch('/api/emails?limit=10');
    if (response.ok) {
      const cache = await caches.open(API_CACHE);
      cache.put('/api/emails?limit=10', response.clone());
      console.log('[SW] Emails synced successfully');
    }
  } catch (error) {
    console.error('[SW] Email sync failed:', error);
  }
}

async function fetchNewEmails() {
  console.log('[SW] Fetching new emails...');

  try {
    const response = await fetch('/api/emails/fetch', { method: 'POST' });

    if (response.ok) {
      const data = await response.json();

      // Notifica l'utente se ci sono nuove email
      if (data.new > 0) {
        self.registration.showNotification('SNALS Mail', {
          body: `${data.new} nuova/e email ricevuta/e`,
          icon: '/icons/icon-192x192.png',
          badge: '/icons/badge-72x72.png',
          tag: 'new-emails',
          data: { url: '/emails' },
        });
      }
    }
  } catch (error) {
    console.error('[SW] Fetch new emails failed:', error);
  }
}

// ============ MESSAGE HANDLER ============
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => caches.delete(cacheName))
        );
      }).then(() => {
        console.log('[SW] All caches cleared');
        event.ports[0].postMessage({ success: true });
      })
    );
  }
});

console.log('[SW] Service Worker loaded');
