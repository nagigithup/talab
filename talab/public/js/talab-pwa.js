(() => {
	const root = document.querySelector("#talab-portal");
	if (!root) return;
	const installButton = document.querySelector("#tp-install");
	const iosHelp = document.querySelector("#tp-ios-install");
	const updateBox = document.querySelector("#tp-update");
	let installPrompt = null;
	let refreshing = false;
	const standalone = matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;
	const ios = /iphone|ipad|ipod/i.test(navigator.userAgent);

	addEventListener("beforeinstallprompt", (event) => {
		event.preventDefault(); installPrompt = event;
		if (!standalone && sessionStorage.getItem("talab.install.dismissed") !== "1") installButton.hidden = false;
	});
	installButton?.addEventListener("click", async () => {
		if (!installPrompt) return;
		installButton.hidden = true; installPrompt.prompt();
		const choice = await installPrompt.userChoice;
		if (choice.outcome !== "accepted") sessionStorage.setItem("talab.install.dismissed", "1");
		installPrompt = null;
	});
	if (ios && !standalone && sessionStorage.getItem("talab.ios.dismissed") !== "1") iosHelp.hidden = false;
	document.querySelector("#tp-ios-dismiss")?.addEventListener("click", () => { iosHelp.hidden = true; sessionStorage.setItem("talab.ios.dismissed", "1"); });
	addEventListener("appinstalled", () => { installButton.hidden = true; iosHelp.hidden = true; });

	if (!("serviceWorker" in navigator)) return;
	navigator.serviceWorker.register("/talab-sw.js", {scope: "/talab"}).then((registration) => {
		const showUpdate = (worker) => {
			if (!navigator.serviceWorker.controller) return;
			updateBox.hidden = false;
			document.querySelector("#tp-update-now").onclick = () => {
				if (root.dataset.transactionBusy === "1") return;
				if (root.querySelector("form") && !confirm("توجد بيانات غير مرسلة. هل تريد التحديث الآن؟")) return;
				worker.postMessage({type: "SKIP_WAITING"});
			};
		};
		if (registration.waiting) showUpdate(registration.waiting);
		registration.addEventListener("updatefound", () => registration.installing?.addEventListener("statechange", () => {
			if (registration.installing?.state === "installed") showUpdate(registration.installing);
		}));
	}).catch(() => {});
	navigator.serviceWorker.addEventListener("controllerchange", () => { if (!refreshing) { refreshing = true; location.reload(); } });
})();
