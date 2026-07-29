(() => {
	const status = document.querySelector("#tp-connection"), install = document.querySelector("#tp-install");
	let installPrompt, checking = false;
	const set = (text, offline = false) => { if (!status) return; status.textContent = text; status.classList.toggle("tp-connection-offline", offline); document.querySelectorAll('[data-action="submit-open"],[data-action="submit-close"]').forEach(button => button.disabled = offline); };
	async function check() { if (checking) return; checking = true; if (!navigator.onLine) { set("غير متصل", true); checking = false; return; } const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), 5000); try { const response = await fetch("/api/method/ping", {cache:"no-store", credentials:"same-origin", signal:controller.signal}); set(response.ok ? "متصل" : "تعذر الوصول إلى الخادم", !response.ok); } catch { set("تعذر الوصول إلى الخادم", true); } finally { clearTimeout(timer); checking = false; } }
	window.addEventListener("online", () => { set("جارٍ إعادة الاتصال"); check(); }); window.addEventListener("offline", () => set("غير متصل", true)); setInterval(check, 60000); check();
	if ("serviceWorker" in navigator) window.addEventListener("load", () => navigator.serviceWorker.register("/assets/talab/talab-sw.js", {scope:"/talab"}).catch(() => {}));
	window.addEventListener("beforeinstallprompt", event => { event.preventDefault(); installPrompt = event; if (install) install.hidden = false; }); install?.addEventListener("click", async () => { if (!installPrompt) return; await installPrompt.prompt(); installPrompt = null; install.hidden = true; });
})();
