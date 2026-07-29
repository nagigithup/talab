const CACHE = "talab-static-v1";
const STATIC = ["/assets/talab/css/talab.css", "/assets/talab/css/mobile_portal.css", "/assets/talab/js/mobile_portal.js", "/assets/talab/icons/talab-192.png", "/assets/talab/icons/talab-512.png"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(STATIC)).then(() => self.skipWaiting())));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("talab-static-") && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())));
self.addEventListener("fetch", event => {
	const request = event.request, url = new URL(request.url);
	if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
	if (STATIC.includes(url.pathname)) event.respondWith(caches.match(request).then(response => response || fetch(request).then(network => { if (network.ok && network.type === "basic") caches.open(CACHE).then(cache => cache.put(request, network.clone())); return network; })));
});
