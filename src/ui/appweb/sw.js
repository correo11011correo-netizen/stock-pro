const CACHE_NAME = 'stock-pro-v1';
const ASSETS = [
  '/appweb/index.html',
  '/appweb/css/style.css',
  '/appweb/js/db-local.js',
  '/appweb/js/sync-engine.js',
  '/appweb/js/app.js',
  '/appweb/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(ASSETS);
    })
  );
});

self.addEventListener('fetch', (event) => {
  // Las llamadas a /api/ siempre deben intentar ir a red.
  if (event.request.url.includes('/api/')) {
    return; 
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Si la red funciona, actualizamos la caché con la nueva versión
        const responseClone = response.clone();
        caches.open(CACHE_NAME).then((cache) => {
          cache.put(event.request, responseClone);
        });
        return response;
      })
      .catch(() => {
        // Si falla la red (Offline), usamos la caché
        return caches.match(event.request);
      })
  );
});
