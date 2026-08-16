document.querySelector("#retry").addEventListener("click", () => location.reload());
addEventListener("online", () => {
	document.querySelector("#status").textContent = "جارٍ إعادة الاتصال";
	location.reload();
});
