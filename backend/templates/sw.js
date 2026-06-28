const CACHE_NAME = 'ada-mobile-v1';
const PRECACHE = ['/mobile'];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
        ))
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.url.includes('/socket.io/')) return;
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});
