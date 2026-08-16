const CACHE_NAME = "talab-shell-v3";
const CACHE_PREFIX = "talab-shell-";
const OFFLINE_URL = "/assets/talab/offline.html";
const STATIC_ASSETS = [
	"/assets/talab/css/talab.css",
	"/assets/talab/css/mobile_portal.css",
	"/assets/talab/css/offline.css",
	"/assets/talab/js/mobile_portal.js",
	"/assets/talab/js/talab-pwa.js",
	"/assets/talab/js/offline.js",
	"/assets/talab/manifest.webmanifest",
	OFFLINE_URL,
	"/assets/talab/icons/talab-32.png",
	"/assets/talab/icons/talab-192.png",
	"/assets/talab/icons/talab-512.png",
	"/assets/talab/icons/talab-maskable-512.png",
	"/assets/talab/icons/talab-apple-180.png",
];
const STATIC_PATHS = new Set(STATIC_ASSETS);

async function cacheStaticAsset(cache, path) {
	const response = await fetch(path, {cache: "reload", credentials: "same-origin"});
	if (!response.ok || response.redirected || response.type !== "basic") throw new Error(`Unsafe shell response: ${path}`);
	const contentType = response.headers.get("content-type") || "";
	const expected = path.endsWith(".png") ? "image/png" : path.endsWith(".css") ? "text/css" : path.endsWith(".js") ? "javascript" : path.endsWith(".webmanifest") ? "application/manifest+json" : "text/html";
	if (!contentType.includes(expected)) throw new Error(`Unexpected shell content type: ${path}`);
	await cache.put(path, response);
}

self.addEventListener("install", (event) => {
	event.waitUntil(caches.open(CACHE_NAME).then((cache) => Promise.all(STATIC_ASSETS.map((path) => cacheStaticAsset(cache, path)))));
});

self.addEventListener("activate", (event) => {
	event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("message", (event) => {
	if (event.data?.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("fetch", (event) => {
	const request = event.request;
	const url = new URL(request.url);
	if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
	if (request.mode === "navigate" && url.pathname.startsWith("/talab")) {
		event.respondWith(fetch(request).catch(() => caches.match(OFFLINE_URL)));
		return;
	}
	if (!STATIC_PATHS.has(url.pathname)) return;
	event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
		const contentType = response.headers.get("content-type") || "";
		if (response.ok && response.type === "basic" && !contentType.includes("text/html")) {
			const copy = response.clone(); caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
		}
		return response;
	})));
});
