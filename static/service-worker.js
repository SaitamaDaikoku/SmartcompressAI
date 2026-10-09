/**
 * Service Worker for SmartCompress AI (PWA support)
 */

const CACHE_NAME = "smartcompress-cache-v1";
const STATIC_ASSETS = [
    "/",
    "/static/css/style.css",
    "/static/js/app.js",
    "/manifest.json",
    "/offline"
];

// Install event: cache static assets
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

// Activate event: clean up stale caches
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
    self.clients.claim();
});

// Fetch event: Network-first with offline fallback for navigation
self.addEventListener("fetch", (event) => {
    // Only handle GET requests
    if (event.request.method !== "GET") return;

    if (event.request.mode === "navigate") {
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match("/offline");
            })
        );
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // If valid response, update cache clone
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseClone);
                    });
                }
                return response;
            })
            .catch(() => {
                return caches.match(event.request);
            })
    );
});
