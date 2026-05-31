// Minimal service worker required for full "Add to Home Screen" support
self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  return self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  // Pass-through network strategy so your live games function seamlessly
  e.respondWith(fetch(e.request));
});
