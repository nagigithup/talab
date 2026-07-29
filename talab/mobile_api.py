"""Permission-checked APIs used exclusively by the Talab operational portal."""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime, today

READ_ROLES = {"Talab System Manager", "Talab Manager", "Cashier", "Mill Operator", "Mercury Custodian", "Accounts Reviewer"}
OPEN_ROLES = {"Talab System Manager", "Talab Manager", "Mill Operator"}
CLOSE_ROLES = {"Talab System Manager", "Talab Manager", "Mercury Custodian"}


def _require(roles):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login is required."), frappe.PermissionError)
	if frappe.session.user == "Administrator":
		return
	if not set(frappe.get_roles()).intersection(roles):
		frappe.throw(_("You do not have permission for this operation."), frappe.PermissionError)


def _serialize_shift(shift):
	return {field: shift.get(field) for field in (
		"name", "shift_date", "mill", "shift_number", "customer", "customer_name", "customer_mobile", "operator",
		"opening_datetime", "closing_datetime", "shift_status", "mercury_issued", "mercury_returned",
		"mercury_shortage", "mercury_exemption", "chargeable_mercury", "mercury_price_per_gram", "mercury_charge",
		"shift_rental_amount", "additional_charges", "total_due", "amount_paid", "outstanding_amount", "payment_status",
		"payment_method", "payment_reference", "notes", "docstatus",
	)}


@frappe.whitelist()
def dashboard_summary(date=None):
	_require(READ_ROLES)
	date = getdate(date or today())
	rows = frappe.get_list(
		"Talab Mill Shift", filters={"shift_date": date, "docstatus": ["<", 2]},
		fields=["shift_status", "total_due", "amount_paid", "outstanding_amount"], limit_page_length=500,
	)
	mills = frappe.get_list("Talab Mill", fields=["current_status"], limit_page_length=20)
	return {
		"date": str(date), "available_mills": sum(m.current_status == "Available" for m in mills),
		"operating_mills": sum(m.current_status == "Operating" for m in mills), "open_shifts": sum(r.shift_status == "Open" for r in rows),
		"closed_shifts": sum(r.shift_status == "Closed" for r in rows), "total_due": sum(flt(r.total_due) for r in rows),
		"total_paid": sum(flt(r.amount_paid) for r in rows), "total_outstanding": sum(flt(r.outstanding_amount) for r in rows),
	}


@frappe.whitelist()
def mill_statuses():
	_require(READ_ROLES)
	mills = frappe.get_list("Talab Mill", fields=["name", "mill_number", "mill_name", "current_status", "current_open_shift", "enabled"], order_by="mill_number")
	for mill in mills:
		if mill.current_open_shift:
			shift = frappe.get_doc("Talab Mill Shift", mill.current_open_shift)
			if shift.has_permission("read"):
				mill.update({"customer_name": shift.customer_name, "shift_number": shift.shift_number, "opening_datetime": shift.opening_datetime})
	return mills


@frappe.whitelist()
def customers(search=None):
	_require(OPEN_ROLES)
	filters = [["Customer", "disabled", "=", 0]]
	if search:
		filters.append(["Customer", "customer_name", "like", f"%{search}%"])
	return frappe.get_list("Customer", filters=filters, fields=["name", "customer_name", "mobile_no"], limit_page_length=20)


@frappe.whitelist()
def open_shifts(mill=None, customer=None, operator=None, search=None):
	_require(READ_ROLES)
	filters = {"shift_status": "Open", "docstatus": 0}
	for field, value in (("mill", mill), ("customer", customer), ("operator", operator)):
		if value:
			filters[field] = value
	rows = frappe.get_list("Talab Mill Shift", filters=filters, fields=["name", "mill", "shift_number", "customer", "customer_name", "customer_mobile", "operator", "opening_datetime", "mercury_issued", "shift_rental_amount"], order_by="opening_datetime asc", limit_page_length=100)
	if search:
		needle = search.casefold()
		rows = [row for row in rows if needle in (row.customer_name or "").casefold() or needle in (row.customer_mobile or "").casefold()]
	return rows


@frappe.whitelist()
def shift_details(name):
	_require(READ_ROLES)
	shift = frappe.get_doc("Talab Mill Shift", name)
	shift.check_permission("read")
	return _serialize_shift(shift)


@frappe.whitelist()
def create_shift(mill, customer, customer_mobile=None, opening_datetime=None, notes=None):
	_require(OPEN_ROLES)
	if not frappe.has_permission("Talab Mill Shift", "create"):
		frappe.throw(_("You do not have permission to open shifts."), frappe.PermissionError)
	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.check_permission("read")
	shift = frappe.get_doc({"doctype": "Talab Mill Shift", "mill": mill, "customer": customer, "customer_mobile": customer_mobile or customer_doc.mobile_no, "operator": frappe.session.user, "opening_datetime": opening_datetime or now_datetime(), "notes": notes})
	shift.insert()
	return _serialize_shift(shift)


@frappe.whitelist()
def close_shift(name, mercury_returned, closing_datetime=None, additional_charges=0, amount_paid=0, payment_method=None, payment_reference=None, notes=None):
	_require(CLOSE_ROLES)
	shift = frappe.get_doc("Talab Mill Shift", name)
	shift.check_permission("write")
	if shift.docstatus != 0 or shift.shift_status != "Open":
		frappe.throw(_("This shift is already closed."), frappe.ValidationError)
	shift.update({"mercury_returned": mercury_returned, "closing_datetime": closing_datetime or now_datetime(), "additional_charges": additional_charges, "amount_paid": amount_paid, "payment_method": payment_method, "payment_reference": payment_reference, "notes": notes})
	shift.submit()
	return _serialize_shift(shift)


@frappe.whitelist()
def daily_summary(date=None):
	_require(READ_ROLES)
	date = getdate(date or today())
	rows = frappe.get_list("Talab Mill Shift", filters={"shift_date": date, "docstatus": ["<", 2]}, fields=["mill", "shift_status", "shift_rental_amount", "mercury_issued", "mercury_returned", "mercury_shortage", "chargeable_mercury", "mercury_charge", "additional_charges", "total_due", "amount_paid", "outstanding_amount", "payment_method"], limit_page_length=500)
	def total(field): return sum(flt(row.get(field)) for row in rows)
	by_mill = {}
	for row in rows:
		entry = by_mill.setdefault(row.mill, {"mill": row.mill, "shifts": 0, "total_due": 0, "paid": 0, "outstanding": 0})
		entry["shifts"] += 1
		entry["total_due"] += flt(row.total_due)
		entry["paid"] += flt(row.amount_paid)
		entry["outstanding"] += flt(row.outstanding_amount)
	return {"date": str(date), "total_shifts": len(rows), "open_shifts": sum(r.shift_status == "Open" for r in rows), "closed_shifts": sum(r.shift_status == "Closed" for r in rows), "mills_operated": len(by_mill), "total_rental_amount": total("shift_rental_amount"), "total_mercury_issued": total("mercury_issued"), "total_mercury_returned": total("mercury_returned"), "total_mercury_shortage": total("mercury_shortage"), "total_chargeable_mercury": total("chargeable_mercury"), "total_mercury_charges": total("mercury_charge"), "total_additional_charges": total("additional_charges"), "total_due": total("total_due"), "total_paid": total("amount_paid"), "total_outstanding": total("outstanding_amount"), "cash_received": sum(flt(r.amount_paid) for r in rows if r.payment_method == "Cash"), "bank_received": sum(flt(r.amount_paid) for r in rows if r.payment_method == "Bank Transfer"), "by_mill": list(by_mill.values())}
