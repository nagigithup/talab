"""Permission-checked APIs for the Arabic Talab operational portal."""

import uuid

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate, now_datetime, today

READ_ROLES = {"Talab System Manager", "Talab Manager", "Cashier", "Mill Operator", "Mercury Custodian", "Accounts Reviewer"}
OPEN_ROLES = {"Talab System Manager", "Talab Manager", "Mill Operator"}
CLOSE_ROLES = {"Talab System Manager", "Talab Manager", "Mercury Custodian"}


def _require(roles):
	if frappe.session.user == "Guest":
		frappe.throw(_("Login is required."), frappe.PermissionError)
	user_roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and not user_roles.intersection(roles):
		frappe.throw(_("You do not have permission for this operation."), frappe.PermissionError)
	return user_roles


def _serialize_shift(shift):
	fields = (
		"name", "shift_date", "mill", "shift_number", "customer", "customer_name", "customer_mobile",
		"operator", "opening_datetime", "closing_datetime", "shift_status", "mercury_issued",
		"mercury_returned", "mercury_shortage", "mercury_exemption", "chargeable_mercury",
		"mercury_price_per_gram", "mercury_charge", "shift_rental_amount", "additional_charges",
		"total_due", "amount_paid", "outstanding_amount", "payment_status", "payment_method",
		"payment_reference", "notes", "docstatus",
	)
	return {field: shift.get(field) for field in fields}


def _settings():
	settings = frappe.get_cached_doc("Talab Settings")
	return {
		"shift_rental_amount": flt(settings.default_shift_rental_amount),
		"mercury_issued": flt(settings.default_mercury_issue_qty),
		"mercury_exemption": flt(settings.default_mercury_exemption_qty),
		"mercury_price_per_gram": flt(settings.mercury_price_per_gram),
		"enable_additional_charges": bool(settings.enable_additional_charges),
		"currency": settings.default_currency or frappe.defaults.get_global_default("currency"),
	}


def _validate_request_id(request_id):
	try:
		value = uuid.UUID(str(request_id))
	except (TypeError, ValueError, AttributeError):
		frappe.throw(_("A valid operation request ID is required."), frappe.ValidationError)
	if value.version != 4 or str(value) != str(request_id).lower():
		frappe.throw(_("A valid operation request ID is required."), frappe.ValidationError)
	return str(value)


def _operation_response(request):
	response = {"request_id": request.request_id, "operation_type": request.operation_type, "status": request.status}
	if request.status == "Completed" and request.result_doctype == "Talab Mill Shift" and request.result_document:
		shift = frappe.get_doc("Talab Mill Shift", request.result_document)
		shift.check_permission("read")
		response["result"] = _serialize_shift(shift)
	return response


def _begin_operation(request_id, operation_type, target_reference):
	request_id = _validate_request_id(request_id)
	if frappe.db.exists("Talab Operation Request", request_id):
		request = frappe.get_doc("Talab Operation Request", request_id)
		request.check_permission("read")
		if request.operation_type != operation_type:
			frappe.throw(_("This request ID belongs to a different operation."), frappe.ValidationError)
		if request.target_reference != target_reference:
			frappe.throw(_("This request ID belongs to a different operation target."), frappe.ValidationError)
		return request, False
	request = frappe.get_doc({"doctype": "Talab Operation Request", "request_id": request_id, "operation_type": operation_type, "target_reference": target_reference, "requested_by": frappe.session.user})
	request.flags.from_talab_api = True
	try:
		request.insert()
	except frappe.DuplicateEntryError:
		request = frappe.get_doc("Talab Operation Request", request_id)
		request.check_permission("read")
		if request.operation_type != operation_type:
			frappe.throw(_("This request ID belongs to a different operation."), frappe.ValidationError)
		if request.target_reference != target_reference:
			frappe.throw(_("This request ID belongs to a different operation target."), frappe.ValidationError)
		return request, False
	return request, True


def _complete_operation(request, result_document):
	request.flags.from_talab_api = True
	request.status = "Completed"
	request.result_doctype = "Talab Mill Shift"
	request.result_document = result_document
	request.save()
	return _operation_response(request)


@frappe.whitelist()
def ping():
	_require(READ_ROLES)
	return {"ok": True, "server_time": now_datetime()}


@frappe.whitelist()
def portal_context():
	roles = _require(READ_ROLES)
	administrator = frappe.session.user == "Administrator"
	return {
		"user": frappe.session.user,
		"full_name": frappe.utils.get_fullname(frappe.session.user),
		"today": str(today()),
		"can_open": administrator or bool(roles.intersection(OPEN_ROLES)),
		"can_close": administrator or bool(roles.intersection(CLOSE_ROLES)),
		"can_review": administrator or "Accounts Reviewer" in roles,
	}


@frappe.whitelist()
def dashboard_summary(date=None):
	_require(READ_ROLES)
	date = getdate(date or today())
	rows = frappe.get_list("Talab Mill Shift", filters={"shift_date": date, "docstatus": ["<", 2]}, fields=["shift_status", "total_due", "amount_paid", "outstanding_amount"], limit_page_length=500)
	mills = frappe.get_list("Talab Mill", fields=["current_status"], limit_page_length=20)
	return {
		"date": str(date),
		"available_mills": sum(m.current_status == "Available" for m in mills),
		"operating_mills": sum(m.current_status == "Operating" for m in mills),
		"open_shifts": sum(r.shift_status == "Open" for r in rows),
		"closed_shifts": sum(r.shift_status == "Closed" for r in rows),
		"total_due": sum(flt(r.total_due) for r in rows),
		"total_paid": sum(flt(r.amount_paid) for r in rows),
		"total_outstanding": sum(flt(r.outstanding_amount) for r in rows),
	}


@frappe.whitelist()
def mill_statuses():
	_require(READ_ROLES)
	mills = frappe.get_list("Talab Mill", fields=["name", "mill_number", "mill_name", "current_status", "current_open_shift", "enabled"], order_by="mill_number", limit_page_length=20)
	for mill in mills:
		if mill.current_open_shift:
			shift = frappe.get_doc("Talab Mill Shift", mill.current_open_shift)
			if shift.has_permission("read"):
				mill.update({"customer_name": shift.customer_name, "shift_number": shift.shift_number, "opening_datetime": shift.opening_datetime})
	return mills


@frappe.whitelist()
def opening_context(mill=None, customer=None):
	_require(OPEN_ROLES)
	result = {"defaults": _settings(), "opening_datetime": now_datetime()}
	if mill:
		mill_doc = frappe.get_doc("Talab Mill", mill)
		mill_doc.check_permission("read")
		if not mill_doc.enabled or mill_doc.current_status != "Available" or mill_doc.current_open_shift:
			frappe.throw(_("This mill is no longer available."), frappe.ValidationError)
		result["mill"] = {"name": mill_doc.name, "mill_number": mill_doc.mill_number, "mill_name": mill_doc.mill_name}
	if customer:
		result["customer"] = customer_details(customer)
	return result


@frappe.whitelist()
def closing_context():
	_require(CLOSE_ROLES)
	return {"defaults": _settings(), "closing_datetime": now_datetime()}


@frappe.whitelist()
def customers(search=None):
	_require(OPEN_ROLES)
	if not frappe.has_permission("Customer", "read"):
		frappe.throw(_("You do not have permission to search customers."), frappe.PermissionError)
	search = (search or "").strip()
	return frappe.get_list(
		"Customer", filters={"disabled": 0},
		or_filters={"name": ["like", f"%{search}%"], "customer_name": ["like", f"%{search}%"], "mobile_no": ["like", f"%{search}%"]},
		fields=["name", "customer_name", "mobile_no"], order_by="customer_name", limit_page_length=20,
	)


@frappe.whitelist()
def customer_details(customer):
	_require(OPEN_ROLES)
	doc = frappe.get_doc("Customer", customer)
	doc.check_permission("read")
	if doc.disabled:
		frappe.throw(_("The selected customer is disabled."), frappe.ValidationError)
	return {"name": doc.name, "customer_name": doc.customer_name, "mobile_no": doc.mobile_no}


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
	now = now_datetime()
	for row in rows:
		row.elapsed_seconds = max(0, int((now - get_datetime(row.opening_datetime)).total_seconds()))
	return rows


@frappe.whitelist()
def shift_details(name):
	_require(READ_ROLES)
	shift = frappe.get_doc("Talab Mill Shift", name)
	shift.check_permission("read")
	return _serialize_shift(shift)


@frappe.whitelist()
def create_shift(mill, customer, request_id=None, customer_mobile=None, opening_datetime=None, notes=None):
	_require(OPEN_ROLES)
	request, is_new = _begin_operation(request_id, "Open Shift", mill)
	if not is_new:
		return _operation_response(request)
	if not frappe.has_permission("Talab Mill Shift", "create"):
		frappe.throw(_("You do not have permission to open shifts."), frappe.PermissionError)
	mill_doc = frappe.get_doc("Talab Mill", mill)
	mill_doc.check_permission("read")
	if not mill_doc.enabled or mill_doc.current_status != "Available" or mill_doc.current_open_shift:
		frappe.throw(_("This mill is no longer available."), frappe.ValidationError)
	customer_doc = frappe.get_doc("Customer", customer)
	customer_doc.check_permission("read")
	shift = frappe.get_doc({"doctype": "Talab Mill Shift", "mill": mill, "customer": customer, "customer_mobile": customer_mobile or customer_doc.mobile_no, "operator": frappe.session.user, "opening_datetime": opening_datetime or now_datetime(), "notes": notes})
	try:
		shift.insert()
	except frappe.DuplicateEntryError:
		frappe.throw(_("Another user opened this mill first. Refresh and try again."), frappe.ValidationError)
	return _complete_operation(request, shift.name)


def _prepare_close(shift, mercury_returned, closing_datetime=None, additional_charges=0, amount_paid=0, payment_method=None, payment_reference=None, notes=None):
	if shift.docstatus != 0 or shift.shift_status != "Open":
		frappe.throw(_("This shift is already closed."), frappe.ValidationError)
	additional_charges = flt(additional_charges)
	if additional_charges and not _settings()["enable_additional_charges"]:
		frappe.throw(_("Additional charges are disabled in Talab Settings."), frappe.ValidationError)
	shift.update({"mercury_returned": mercury_returned, "closing_datetime": closing_datetime or now_datetime(), "additional_charges": additional_charges, "amount_paid": amount_paid, "payment_method": payment_method, "payment_reference": payment_reference, "notes": notes if notes is not None else shift.notes})
	shift._calculate_values()
	shift._validate_input()
	return shift


@frappe.whitelist()
def closing_preview(name, mercury_returned, closing_datetime=None, additional_charges=0, amount_paid=0, payment_method=None, payment_reference=None):
	_require(CLOSE_ROLES)
	shift = frappe.get_doc("Talab Mill Shift", name)
	shift.check_permission("write")
	preview = frappe.copy_doc(shift)
	_prepare_close(preview, mercury_returned, closing_datetime, additional_charges, amount_paid, payment_method, payment_reference)
	return _serialize_shift(preview)


@frappe.whitelist()
def close_shift(name, mercury_returned, request_id=None, closing_datetime=None, additional_charges=0, amount_paid=0, payment_method=None, payment_reference=None, notes=None):
	_require(CLOSE_ROLES)
	request, is_new = _begin_operation(request_id, "Close Shift", name)
	if not is_new:
		return _operation_response(request)
	shift = frappe.get_doc("Talab Mill Shift", name)
	shift.check_permission("write")
	_prepare_close(shift, mercury_returned, closing_datetime, additional_charges, amount_paid, payment_method, payment_reference, notes)
	shift.submit()
	return _complete_operation(request, shift.name)


@frappe.whitelist()
def operation_status(request_id):
	_require(READ_ROLES)
	request_id = _validate_request_id(request_id)
	if not frappe.db.exists("Talab Operation Request", request_id):
		return {"request_id": request_id, "status": "Not Found"}
	request = frappe.get_doc("Talab Operation Request", request_id)
	request.check_permission("read")
	return _operation_response(request)


@frappe.whitelist()
def daily_summary(date=None):
	_require(READ_ROLES)
	date = getdate(date or today())
	fields = ["mill", "shift_status", "shift_rental_amount", "mercury_issued", "mercury_returned", "mercury_shortage", "chargeable_mercury", "mercury_charge", "additional_charges", "total_due", "amount_paid", "outstanding_amount", "payment_method"]
	rows = frappe.get_list("Talab Mill Shift", filters={"shift_date": date, "docstatus": ["<", 2]}, fields=fields, limit_page_length=500)

	def total(field):
		return sum(flt(row.get(field)) for row in rows)

	by_mill = {}
	for row in rows:
		entry = by_mill.setdefault(row.mill, {"mill": row.mill, "shifts": 0, "total_due": 0, "paid": 0, "outstanding": 0})
		entry["shifts"] += 1
		entry["total_due"] += flt(row.total_due)
		entry["paid"] += flt(row.amount_paid)
		entry["outstanding"] += flt(row.outstanding_amount)
	return {
		"date": str(date), "total_shifts": len(rows),
		"open_shifts": sum(r.shift_status == "Open" for r in rows),
		"closed_shifts": sum(r.shift_status == "Closed" for r in rows), "mills_operated": len(by_mill),
		"total_rental_amount": total("shift_rental_amount"), "total_mercury_issued": total("mercury_issued"),
		"total_mercury_returned": total("mercury_returned"), "total_mercury_shortage": total("mercury_shortage"),
		"total_chargeable_mercury": total("chargeable_mercury"), "total_mercury_charges": total("mercury_charge"),
		"total_additional_charges": total("additional_charges"), "total_due": total("total_due"),
		"total_paid": total("amount_paid"), "total_outstanding": total("outstanding_amount"),
		"cash_received": sum(flt(r.amount_paid) for r in rows if r.payment_method == "Cash"),
		"bank_received": sum(flt(r.amount_paid) for r in rows if r.payment_method == "Bank Transfer"),
		"by_mill": sorted(by_mill.values(), key=lambda row: int(row["mill"])),
	}
