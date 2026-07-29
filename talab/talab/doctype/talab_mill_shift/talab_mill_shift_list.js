frappe.listview_settings["Talab Mill Shift"] = {
	add_fields: ["shift_status", "payment_status"],
	get_indicator(doc) {
		if (doc.shift_status === "Open") return [__("Open"), "orange", "shift_status,=,Open"];
		if (doc.payment_status === "Paid") return [__("Paid"), "green", "payment_status,=,Paid"];
		if (doc.payment_status === "Unpaid") return [__("Unpaid"), "red", "payment_status,=,Unpaid"];
		return [__(doc.shift_status), "blue", "shift_status,=," + doc.shift_status];
	},
};
