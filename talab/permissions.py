import frappe


def get_mill_shift_permission_query_conditions(user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if roles.intersection({"Talab System Manager", "Talab Manager", "Mercury Custodian", "Cashier", "Accounts Reviewer"}):
		return None
	if "Mill Operator" in roles:
		return "(`tabTalab Mill Shift`.`operator` = {user} OR `tabTalab Mill Shift`.`owner` = {user})".format(
			user=frappe.db.escape(user)
		)
	return "1=0"


def has_mill_shift_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if roles.intersection({"Talab System Manager", "Talab Manager", "Mercury Custodian", "Cashier", "Accounts Reviewer"}):
		return True
	return "Mill Operator" in roles and (doc.operator == user or doc.owner == user)


def get_operation_request_permission_query_conditions(user=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if user == "Administrator" or roles.intersection({"Talab System Manager", "Talab Manager"}):
		return None
	return "`tabTalab Operation Request`.`requested_by` = {}".format(frappe.db.escape(user))


def has_operation_request_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	roles = set(frappe.get_roles(user))
	if permission_type == "create":
		return user == "Administrator" or bool(roles.intersection({"Talab System Manager", "Talab Manager", "Mill Operator", "Mercury Custodian"}))
	return user == "Administrator" or bool(roles.intersection({"Talab System Manager", "Talab Manager"})) or doc.requested_by == user
