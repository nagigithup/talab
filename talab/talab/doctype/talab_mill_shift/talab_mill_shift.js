frappe.ui.form.on("Talab Mill Shift", {
	refresh(frm) {
		frm.toggle_display("closing_datetime", frm.doc.docstatus === 1 || frm.doc.shift_status === "Closed");
		frm.toggle_display("mercury_returned", frm.doc.docstatus === 1 || frm.doc.shift_status === "Closed");
		if (frm.doc.docstatus === 0 && !frm.is_new()) {
			frm.add_custom_button(__("Close Shift"), () => {
				frm.set_value("shift_status", "Closed");
				frm.set_value("closing_datetime", frappe.datetime.now_datetime());
				frm.save("Submit");
			});
		}
	},
	mill(frm) {
		frm.set_query("mill", () => ({ filters: { enabled: 1, current_status: ["in", ["Available", "Operating"]] } }));
	},
	mercury_issued: calculate_preview,
	mercury_returned: calculate_preview,
	mercury_exemption: calculate_preview,
	mercury_price_per_gram: calculate_preview,
	shift_rental_amount: calculate_preview,
	additional_charges: calculate_preview,
	amount_paid: calculate_preview,
});

function calculate_preview(frm) {
	const shortage = Math.max((frm.doc.mercury_issued || 0) - (frm.doc.mercury_returned || 0), 0);
	const chargeable = Math.max(shortage - (frm.doc.mercury_exemption || 0), 0);
	const charge = chargeable * (frm.doc.mercury_price_per_gram || 0);
	const total = (frm.doc.shift_rental_amount || 0) + charge + (frm.doc.additional_charges || 0);
	frm.set_value("mercury_shortage", shortage);
	frm.set_value("chargeable_mercury", chargeable);
	frm.set_value("mercury_charge", charge);
	frm.set_value("total_due", total);
	frm.set_value("outstanding_amount", total - (frm.doc.amount_paid || 0));
}
