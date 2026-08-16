(() => {
	const root = document.querySelector("#talab-portal");
	if (!root) return;
	const view = document.querySelector("#tp-view");
	const message = document.querySelector("#tp-message");
	const connection = document.querySelector("#tp-connection");
	let context = null;
	let busy = false;
	let serverReachable = false;
	let connectionCheck = null;
	const lastConnectionKey = "talab.lastConnection";

	const labels = {
		Available: "متاحة", Operating: "تعمل الآن", Maintenance: "صيانة", Disabled: "متوقفة",
		Open: "مفتوحة", Closed: "مغلقة", Cancelled: "ملغاة", Unpaid: "غير مدفوع",
		"Partially Paid": "مدفوع جزئياً", Paid: "مدفوع بالكامل", Cash: "نقدي",
		"Bank Transfer": "تحويل بنكي",
	};
	const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[char]));
	const money = (value) => new Intl.NumberFormat("ar", {maximumFractionDigits: 2}).format(Number(value) || 0);
	const formatDate = (value) => value ? new Intl.DateTimeFormat("ar", {dateStyle: "medium", timeStyle: "short"}).format(new Date(String(value).replace(" ", "T"))) : "—";
	const localDatetime = (value = new Date()) => {
		const date = value instanceof Date ? value : new Date(String(value).replace(" ", "T"));
		const offset = date.getTimezoneOffset();
		return new Date(date.getTime() - offset * 60000).toISOString().slice(0, 16);
	};
	const duration = (seconds) => {
		const minutes = Math.floor((Number(seconds) || 0) / 60);
		return `${Math.floor(minutes / 60)} س ${minutes % 60} د`;
	};
	const newRequestId = () => crypto.randomUUID ? crypto.randomUUID() : "10000000-1000-4000-8000-100000000000".replace(/[018]/g, (char) => (Number(char) ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> Number(char) / 4).toString(16));
	const button = (label, action, className = "") => `<button type="button" class="tp-button ${className}" data-action="${escapeHtml(action)}">${escapeHtml(label)}</button>`;

	function api(method, args = {}, timeout = 12000) {
		let timer;
		const request = frappe.call({method: `talab.mobile_api.${method}`, args}).then((response) => response.message);
		const deadline = new Promise((_, reject) => { timer = setTimeout(() => { const error = new Error("انتهت مهلة الاتصال بالخادم."); error.uncertain = true; reject(error); }, timeout); });
		return Promise.race([request, deadline]).finally(() => clearTimeout(timer));
	}
	function errorText(error) {
		try {
			const messages = JSON.parse(error?._server_messages || "[]");
			if (messages.length) return JSON.parse(messages[0]).message;
		} catch (_) { /* use fallback */ }
		return error?.message || "حدث خطأ غير متوقع. حاول مرة أخرى.";
	}
	function notify(text, isError = false) {
		message.innerHTML = `<div class="tp-message ${isError ? "tp-error" : "tp-success"}">${escapeHtml(text)}</div>`;
		message.scrollIntoView({behavior: "smooth", block: "nearest"});
	}
	function clearMessage() { message.innerHTML = ""; }
	function loading(text = "جارٍ تحميل البيانات…") { view.innerHTML = `<div class="tp-loading" role="status">${escapeHtml(text)}</div>`; }
	function empty(text) { return `<div class="tp-empty">${escapeHtml(text)}</div>`; }
	function kv(items, className = "") {
		return `<dl class="tp-kv ${className}">${items.map(([label, value]) => `<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value ?? "—")}</dd></div>`).join("")}</dl>`;
	}

	function setConnectionState(state) {
		const states = {online: ["متصل", "tp-online"], weak: ["الاتصال ضعيف", "tp-weak"], offline: ["غير متصل", "tp-offline"], reconnecting: ["جارٍ إعادة الاتصال", "tp-weak"], unreachable: ["تعذر الوصول إلى الخادم", "tp-offline"]};
		[connection.textContent, connection.className] = states[state];
		serverReachable = state === "online" || state === "weak";
		root.classList.toggle("tp-offline-mode", !serverReachable);
		root.querySelectorAll("#open-form button[type=submit],#close-form button[type=submit]").forEach((button) => { button.disabled = !serverReachable || busy; });
	}
	function offlineState() {
		const activeForm = view.querySelector("#open-form,#close-form");
		if (activeForm) { notify("الاتصال غير متاح. احتفظنا بالمدخلات في هذه الصفحة، ولن يتم إرسالها تلقائياً.", true); return; }
		const last = sessionStorage.getItem(lastConnectionKey);
		view.innerHTML = `<div class="tp-offline-panel"><h2>لا يوجد اتصال بالإنترنت حالياً</h2><p>لا يمكن عرض بيانات تشغيلية حديثة أو فتح وردية أو إغلاقها حتى يعود الاتصال.</p><p>${last ? `آخر اتصال ناجح: ${escapeHtml(new Date(last).toLocaleString("ar"))}` : "لم يتم تسجيل اتصال ناجح في هذه الجلسة."}</p>${button("إعادة المحاولة", "retry", "tp-primary")}</div>`;
	}
	async function checkConnection(reconnecting = false) {
		if (connectionCheck) return connectionCheck;
		if (!navigator.onLine) { setConnectionState("offline"); offlineState(); return false; }
		setConnectionState(reconnecting ? "reconnecting" : "reconnecting");
		const started = performance.now();
		connectionCheck = api("ping", {}, 5000).then(() => {
			const weak = performance.now() - started > 1500;
			setConnectionState(weak ? "weak" : "online");
			sessionStorage.setItem(lastConnectionKey, new Date().toISOString());
			return true;
		}).catch(() => { setConnectionState(navigator.onLine ? "unreachable" : "offline"); offlineState(); return false; }).finally(() => { connectionCheck = null; });
		return connectionCheck;
	}

	async function home() {
		clearMessage(); loading();
		const [summary, mills] = await Promise.all([api("dashboard_summary"), api("mill_statuses")]);
		document.querySelector("#tp-date").textContent = summary.date;
		const actions = [
			context.can_open ? ["فتح وردية جديدة", "open", "tp-primary"] : null,
			["الورديات المفتوحة", "shifts", ""],
			context.can_close ? ["إغلاق وردية", "shifts", ""] : null,
			["ملخص اليوم", "summary", ""],
		].filter(Boolean);
		const cards = [
			["عدد الطواحين المتاحة", summary.available_mills], ["عدد الطواحين المشغلة", summary.operating_mills],
			["عدد الورديات المفتوحة", summary.open_shifts], ["عدد الورديات المغلقة اليوم", summary.closed_shifts],
			["إجمالي مستحقات اليوم", money(summary.total_due)], ["المحصل اليوم", money(summary.total_paid)],
			["المتبقي اليوم", money(summary.total_outstanding)],
		];
		view.innerHTML = `
			<div class="tp-actions">${actions.map(([label, action, cls]) => button(label, action, cls)).join("")}</div>
			<div class="tp-summary-grid">${cards.map(([label, value]) => `<article class="tp-card tp-summary"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`).join("")}</div>
			<div class="tp-section-title"><h2>حالة الطواحين</h2><button type="button" class="tp-link" data-action="home">تحديث</button></div>
			<div class="tp-mill-grid">${mills.map((mill) => {
				const actionable = (mill.current_status === "Available" && context.can_open) || (mill.current_status === "Operating" && mill.current_open_shift);
				return `<button type="button" class="tp-mill tp-${mill.current_status.toLowerCase()}" data-mill="${escapeHtml(mill.name)}" data-status="${escapeHtml(mill.current_status)}" data-shift="${escapeHtml(mill.current_open_shift || "")}" ${actionable ? "" : "disabled"}>
					<strong>طاحونة رقم ${escapeHtml(mill.mill_number)}</strong><span class="tp-status">${escapeHtml(labels[mill.current_status])}</span>
					${mill.customer_name ? `<small>${escapeHtml(mill.customer_name)}</small><small>وردية ${escapeHtml(mill.shift_number)} · ${escapeHtml(formatDate(mill.opening_datetime))}</small>` : ""}
				</button>`;
			}).join("")}</div>`;
	}

	async function openForm(selectedMill = "") {
		if (!context.can_open) throw new Error("ليس لديك صلاحية فتح وردية.");
		if (!serverReachable) { offlineState(); return; }
		loading("جارٍ تجهيز نموذج فتح الوردية…");
		const [mills, opening] = await Promise.all([api("mill_statuses"), api("opening_context", selectedMill ? {mill: selectedMill} : {})]);
		const available = mills.filter((mill) => mill.enabled && mill.current_status === "Available" && !mill.current_open_shift);
		if (!available.length) { view.innerHTML = empty("لا توجد طاحونة متاحة حالياً.") + button("العودة للرئيسية", "home"); return; }
		const defaults = opening.defaults;
		view.innerHTML = `
			<div class="tp-section-title"><h2>فتح وردية جديدة</h2>${button("إلغاء", "home", "tp-secondary")}</div>
			<form class="tp-form" id="open-form"><input type="hidden" name="request_id" value="${newRequestId()}">
				<label>الطاحونة<select name="mill" required>${available.map((mill) => `<option value="${escapeHtml(mill.name)}" ${mill.name === selectedMill ? "selected" : ""}>طاحونة رقم ${escapeHtml(mill.mill_number)}</option>`).join("")}</select></label>
				<label>العميل<input name="customer_search" type="search" autocomplete="off" placeholder="اكتب اسم العميل أو الهاتف" required aria-controls="customer-results"><input name="customer" type="hidden"></label>
				<div id="customer-results" class="tp-search-results"></div>
				<div class="tp-two"><label>اسم العميل<input name="customer_name" readonly></label><label>هاتف العميل<input name="customer_mobile" inputmode="tel" readonly></label></div>
				<div class="tp-two"><label>المشغل<input value="${escapeHtml(context.full_name)}" readonly></label><label>وقت الفتح<input name="opening_datetime" type="datetime-local" value="${localDatetime(opening.opening_datetime)}" readonly></label></div>
				<div class="tp-two"><label>إيجار الوردية<input value="${money(defaults.shift_rental_amount)}" readonly></label><label>الزئبق المصروف<input value="${money(defaults.mercury_issued)}" readonly></label></div>
				<div class="tp-two"><label>إعفاء الزئبق<input value="${money(defaults.mercury_exemption)}" readonly></label><label>سعر جرام الزئبق<input value="${money(defaults.mercury_price_per_gram)}" readonly></label></div>
				<label>ملاحظات اختيارية<textarea name="notes" rows="3"></textarea></label>
				<div class="tp-confirm" id="open-confirm">اختر العميل لعرض ملخص التأكيد.</div>
				<div class="tp-sticky"><button type="submit" class="tp-button tp-primary">فتح الوردية</button></div>
			</form>`;
		const form = view.querySelector("#open-form");
		const search = form.elements.customer_search;
		let timer;
		search.addEventListener("input", () => {
			form.elements.customer.value = ""; form.elements.customer_name.value = ""; form.elements.customer_mobile.value = "";
			clearTimeout(timer);
			timer = setTimeout(async () => {
				try {
					const rows = await api("customers", {search: search.value});
					view.querySelector("#customer-results").innerHTML = rows.length ? rows.map((row) => `<button type="button" data-customer="${escapeHtml(row.name)}" data-name="${escapeHtml(row.customer_name || row.name)}" data-mobile="${escapeHtml(row.mobile_no || "")}"><strong>${escapeHtml(row.customer_name || row.name)}</strong><small>${escapeHtml(row.mobile_no || row.name)}</small></button>`).join("") : empty("لا توجد نتائج.");
				} catch (error) { notify(errorText(error), true); }
			}, 250);
		});
		view.querySelector("#customer-results").addEventListener("click", (event) => {
			const row = event.target.closest("[data-customer]"); if (!row) return;
			form.elements.customer.value = row.dataset.customer; form.elements.customer_name.value = row.dataset.name;
			form.elements.customer_mobile.value = row.dataset.mobile; search.value = row.dataset.name;
			view.querySelector("#customer-results").innerHTML = "";
			view.querySelector("#open-confirm").innerHTML = kv([["الطاحونة", form.elements.mill.value], ["العميل", row.dataset.name], ["الزئبق المصروف", defaults.mercury_issued], ["إيجار الوردية", money(defaults.shift_rental_amount)]]);
		});
	}

	async function shifts(filters = {}) {
		loading();
		const [rows, mills] = await Promise.all([api("open_shifts", filters), api("mill_statuses")]);
		view.innerHTML = `
			<div class="tp-section-title"><h2>الورديات المفتوحة</h2>${button("العودة للرئيسية", "home", "tp-secondary")}</div>
			<form id="shift-filters" class="tp-filters"><select name="mill"><option value="">كل الطواحين</option>${mills.map((mill) => `<option value="${escapeHtml(mill.name)}">طاحونة ${escapeHtml(mill.mill_number)}</option>`).join("")}</select><input name="operator" placeholder="المشغل"><input name="search" type="search" placeholder="اسم العميل أو الهاتف"><button class="tp-button" type="submit">بحث</button></form>
			<div class="tp-list">${rows.length ? rows.map((shift) => `<article class="tp-row"><div class="tp-row-title"><h3>طاحونة ${escapeHtml(shift.mill)} · وردية ${escapeHtml(shift.shift_number)}</h3><span class="tp-badge">${escapeHtml(duration(shift.elapsed_seconds))}</span></div>${kv([["العميل", shift.customer_name], ["الهاتف", shift.customer_mobile], ["المشغل", shift.operator], ["وقت الفتح", formatDate(shift.opening_datetime)], ["الزئبق المصروف", shift.mercury_issued], ["الإيجار المتوقع", money(shift.shift_rental_amount)]])}<div class="tp-row-actions">${button("عرض التفاصيل", `details:${shift.name}`)}${context.can_close ? button("إغلاق الوردية", `close:${shift.name}`, "tp-primary") : ""}</div></article>`).join("") : empty("لا توجد ورديات مفتوحة مطابقة.")}</div>`;
	}

	function detailsMarkup(shift) {
		return kv([
			["معرّف الوردية", shift.name], ["تاريخ الوردية", shift.shift_date], ["الطاحونة", shift.mill], ["رقم الوردية", shift.shift_number],
			["العميل", shift.customer_name], ["الهاتف", shift.customer_mobile], ["المشغل", shift.operator], ["وقت الفتح", formatDate(shift.opening_datetime)],
			["وقت الإغلاق", formatDate(shift.closing_datetime)], ["الزئبق المصروف", shift.mercury_issued], ["الزئبق المرتجع", shift.mercury_returned],
			["العجز", shift.mercury_shortage], ["الإعفاء", shift.mercury_exemption], ["الخاضع للرسوم", shift.chargeable_mercury],
			["سعر جرام الزئبق", money(shift.mercury_price_per_gram)], ["رسوم الزئبق", money(shift.mercury_charge)], ["إيجار الوردية", money(shift.shift_rental_amount)],
			["الرسوم الإضافية", money(shift.additional_charges)], ["إجمالي المستحق", money(shift.total_due)], ["المدفوع", money(shift.amount_paid)],
			["المتبقي", money(shift.outstanding_amount)], ["حالة الدفع", labels[shift.payment_status]], ["طريقة الدفع", labels[shift.payment_method]],
			["مرجع الدفع", shift.payment_reference], ["حالة الوردية", labels[shift.shift_status]],
		]);
	}

	async function details(name) {
		loading(); const shift = await api("shift_details", {name});
		view.innerHTML = `<div class="tp-section-title"><h2>تفاصيل الوردية</h2></div>${detailsMarkup(shift)}<div class="tp-actions">${button("العودة للرئيسية", "home")}${button("طباعة", "print", "tp-secondary")}${shift.shift_status === "Open" && context.can_close ? button("إغلاق الوردية", `close:${shift.name}`, "tp-primary") : ""}</div>`;
	}

	async function closeForm(name) {
		if (!context.can_close) throw new Error("ليس لديك صلاحية إغلاق وردية.");
		if (!serverReachable) { offlineState(); return; }
		loading(); const [shift, opening] = await Promise.all([api("shift_details", {name}), api("closing_context")]);
		view.innerHTML = `
			<div class="tp-section-title"><h2>إغلاق وردية طاحونة ${escapeHtml(shift.mill)}</h2>${button("إلغاء", `details:${name}`, "tp-secondary")}</div>
			${kv([["رقم الوردية", shift.shift_number], ["العميل", shift.customer_name], ["الهاتف", shift.customer_mobile], ["وقت الفتح", formatDate(shift.opening_datetime)], ["الزئبق المصروف", shift.mercury_issued], ["الإعفاء", shift.mercury_exemption], ["سعر الجرام", money(shift.mercury_price_per_gram)], ["إيجار الوردية", money(shift.shift_rental_amount)]], "tp-readonly")}
			<form class="tp-form" id="close-form"><input type="hidden" name="name" value="${escapeHtml(name)}"><input type="hidden" name="request_id" value="${newRequestId()}">
				<label>وقت الإغلاق<input type="datetime-local" name="closing_datetime" value="${localDatetime()}" required></label>
				<label>الزئبق المرتجع<input type="number" name="mercury_returned" min="0" max="${escapeHtml(shift.mercury_issued)}" step="0.01" inputmode="decimal" required></label>
				${opening.defaults.enable_additional_charges ? `<label>رسوم إضافية<input type="number" name="additional_charges" min="0" step="0.01" value="0" inputmode="decimal"></label>` : `<input type="hidden" name="additional_charges" value="0">`}
				<label>المبلغ المدفوع<input type="number" name="amount_paid" min="0" step="0.01" value="0" inputmode="decimal" required></label>
				<label>طريقة الدفع<select name="payment_method" required><option value="Cash">نقدي</option><option value="Bank Transfer">تحويل بنكي</option></select></label>
				<label class="tp-payment-reference" hidden>مرجع التحويل<input name="payment_reference"></label><label>ملاحظات<textarea name="notes" rows="3">${escapeHtml(shift.notes || "")}</textarea></label>
				<div><h3>المعاينة</h3><div id="close-preview" class="tp-confirm">أدخل الزئبق المرتجع لاحتساب القيم.</div></div>
				<div class="tp-sticky"><button type="submit" class="tp-button tp-primary">إغلاق الوردية</button></div>
			</form>`;
		const form = view.querySelector("#close-form"); let timer;
		const updatePreview = () => { clearTimeout(timer); timer = setTimeout(async () => {
			if (form.elements.mercury_returned.value === "") return;
			try { const preview = await api("closing_preview", Object.fromEntries(new FormData(form))); form.dataset.preview = JSON.stringify(preview); view.querySelector("#close-preview").innerHTML = detailsMarkup(preview); }
			catch (error) { view.querySelector("#close-preview").innerHTML = `<div class="tp-error">${escapeHtml(errorText(error))}</div>`; }
		}, 250); };
		form.addEventListener("input", updatePreview);
		form.elements.payment_method.addEventListener("change", () => { const bank = form.elements.payment_method.value === "Bank Transfer"; const label = form.querySelector(".tp-payment-reference"); label.hidden = !bank; form.elements.payment_reference.required = bank; updatePreview(); });
	}

	async function summary(date = "") {
		loading(); const result = await api("daily_summary", date ? {date} : {});
		const items = [["إجمالي الورديات", result.total_shifts], ["الورديات المفتوحة", result.open_shifts], ["الورديات المغلقة", result.closed_shifts], ["الطواحين المشغلة", result.mills_operated], ["إجمالي الإيجار", money(result.total_rental_amount)], ["الزئبق المصروف", result.total_mercury_issued], ["الزئبق المرتجع", result.total_mercury_returned], ["عجز الزئبق", result.total_mercury_shortage], ["الزئبق الخاضع", result.total_chargeable_mercury], ["رسوم الزئبق", money(result.total_mercury_charges)], ["الرسوم الإضافية", money(result.total_additional_charges)], ["إجمالي المستحق", money(result.total_due)], ["إجمالي المدفوع", money(result.total_paid)], ["إجمالي المتبقي", money(result.total_outstanding)], ["المستلم نقداً", money(result.cash_received)], ["التحويلات البنكية", money(result.bank_received)]];
		view.innerHTML = `<div class="tp-section-title"><h2>الملخص اليومي</h2>${button("العودة للرئيسية", "home", "tp-secondary")}</div><form id="summary-filter" class="tp-date-filter"><label>التاريخ<input type="date" name="date" value="${escapeHtml(result.date)}"></label><button class="tp-button" type="submit">عرض</button></form><div class="tp-summary-grid">${items.map(([label, value]) => `<article class="tp-card tp-summary"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></article>`).join("")}</div><h3>التفصيل حسب الطاحونة</h3><div class="tp-table-wrap"><table><thead><tr><th>الطاحونة</th><th>الورديات</th><th>المستحق</th><th>المدفوع</th><th>المتبقي</th></tr></thead><tbody>${result.by_mill.length ? result.by_mill.map((row) => `<tr><td>${escapeHtml(row.mill)}</td><td>${escapeHtml(row.shifts)}</td><td>${money(row.total_due)}</td><td>${money(row.paid)}</td><td>${money(row.outstanding)}</td></tr>`).join("") : `<tr><td colspan="5">لا توجد بيانات لهذا التاريخ.</td></tr>`}</tbody></table></div>`;
	}

	async function verifyOperation(requestId) {
		if (!await checkConnection(true)) return;
		try {
			const operation = await api("operation_status", {request_id: requestId}, 10000);
			if (operation.status === "Not Found") { notify("لم تصل العملية إلى الخادم، راجع البيانات ثم أعد المحاولة.", true); return; }
			if (operation.status === "Completed" && operation.result) {
				notify("تمت العملية بنجاح. العملية مسجلة مسبقاً.");
				return details(operation.result.name);
			}
			notify("حالة العملية غير مؤكدة، اضغط للتحقق مرة أخرى.", true);
		} catch (error) {
			const text = errorText(error);
			if (/does not exist|not found|غير موجود/i.test(text)) notify("لم تصل العملية إلى الخادم، راجع البيانات ثم أعد المحاولة.", true);
			else notify("حالة العملية غير مؤكدة، اضغط للتحقق مرة أخرى.", true);
		}
	}

	root.addEventListener("click", async (event) => {
		const target = event.target.closest("[data-action], .tp-mill"); if (!target || busy) return;
		try {
			clearMessage(); const action = target.dataset.action;
			if (target.dataset.mill) return target.dataset.status === "Available" ? openForm(target.dataset.mill) : details(target.dataset.shift);
			if (action === "home") return home(); if (action === "retry") { if (await checkConnection(true)) return home(); return; } if (action === "open") return openForm(); if (action === "shifts") return shifts(); if (action === "summary") return summary(); if (action === "print") return window.print();
			const [name, id] = action.split(":"); if (name === "details") return details(id); if (name === "close") return closeForm(id);
			if (name === "verify") return verifyOperation(id);
		} catch (error) { notify(errorText(error), true); }
	});

	root.addEventListener("submit", async (event) => {
		event.preventDefault(); const form = event.target;
		if (form.id === "shift-filters") return shifts(Object.fromEntries(new FormData(form)));
		if (form.id === "summary-filter") return summary(form.elements.date.value);
		if (!serverReachable) { notify("لا يمكن إرسال العملية دون اتصال مؤكد بالخادم.", true); return; }
		if (busy) return; const submit = form.querySelector('[type="submit"]');
		try {
			busy = true; root.dataset.transactionBusy = "1"; submit.disabled = true; submit.textContent = "جارٍ إرسال العملية، يرجى عدم إغلاق الصفحة";
			const data = Object.fromEntries(new FormData(form));
			if (form.id === "open-form") {
				if (!data.customer) throw new Error("اختر عميلاً من نتائج البحث.");
				if (!window.confirm(`تأكيد فتح الوردية؟\nالطاحونة: ${data.mill}\nالعميل: ${form.elements.customer_name.value}`)) return;
				delete data.customer_search; delete data.customer_name;
				const operation = await api("create_shift", data, 30000); const shift = operation.result;
				view.innerHTML = `<div class="tp-success-panel"><h2>تم فتح الوردية بنجاح</h2>${kv([["معرّف الوردية", shift.name], ["رقم الوردية", shift.shift_number]])}<div class="tp-actions">${button("العودة للرئيسية", "home")}${button("عرض الوردية", `details:${shift.name}`, "tp-primary")}</div></div>`;
			} else if (form.id === "close-form") {
				if (!form.dataset.preview) throw new Error("أكمل الحقول وانتظر ظهور المعاينة قبل الإغلاق.");
				const preview = JSON.parse(form.dataset.preview);
				if (!window.confirm(`تأكيد إغلاق الوردية؟\nالمرتجع: ${preview.mercury_returned}\nالعجز: ${preview.mercury_shortage}\nالخاضع: ${preview.chargeable_mercury}\nرسوم الزئبق: ${money(preview.mercury_charge)}\nالإيجار: ${money(preview.shift_rental_amount)}\nالإجمالي: ${money(preview.total_due)}\nالمدفوع: ${money(preview.amount_paid)}\nالمتبقي: ${money(preview.outstanding_amount)}\nطريقة الدفع: ${labels[preview.payment_method]}`)) return;
				const operation = await api("close_shift", data, 30000); const shift = operation.result;
				notify("تم إغلاق الوردية وإرسالها بنجاح."); await details(shift.name);
			}
		} catch (error) {
			if (error.uncertain || !navigator.onLine) {
				const requestId = form.elements.request_id.value;
				notify("حالة العملية غير مؤكدة. لا تنشئ عملية جديدة قبل التحقق.", true);
				message.insertAdjacentHTML("beforeend", button("التحقق من حالة العملية", `verify:${requestId}`, "tp-primary"));
			} else notify(errorText(error), true);
		}
		finally { busy = false; root.dataset.transactionBusy = "0"; submit.disabled = !serverReachable; submit.textContent = form.id === "open-form" ? "فتح الوردية" : "إغلاق الوردية"; }
	});

	window.addEventListener("online", () => checkConnection(true)); window.addEventListener("offline", () => { setConnectionState("offline"); offlineState(); });
	setInterval(() => checkConnection(false), 30000);
	document.querySelector("#tp-logout")?.addEventListener("click", () => { Object.keys(sessionStorage).filter((key) => key.startsWith("talab.")).forEach((key) => sessionStorage.removeItem(key)); });
	(async () => { try { context = await api("portal_context"); await Promise.all([home(), checkConnection()]); } catch (error) { notify(errorText(error), true); view.innerHTML = empty("تعذر تحميل بوابة طلب."); } })();
})();
