frappe.query_reports["Daily Mill Shift Summary"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
		{ fieldname: "mill", label: __("Mill"), fieldtype: "Link", options: "Talab Mill" },
		{ fieldname: "customer", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "shift_status", label: __("Shift Status"), fieldtype: "Select", options: "\nOpen\nClosed\nCancelled" },
		{ fieldname: "payment_status", label: __("Payment Status"), fieldtype: "Select", options: "\nUnpaid\nPartially Paid\nPaid" },
	],
};
