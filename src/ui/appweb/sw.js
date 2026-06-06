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
  // Solo cacheamos assets estáticos. Las llamadas a /api/ siempre deben intentar ir a red.
  if (event.request.url.includes('/api/')) {
    return; 
  }

  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
