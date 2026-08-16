import frappe

from talab.mobile_api import READ_ROLES

login_required = True
no_cache = 1


def get_context(context):
	roles = set(frappe.get_roles())
	if frappe.session.user != "Administrator" and not roles.intersection(READ_ROLES):
		frappe.throw("ليس لديك صلاحية للوصول إلى بوابة طلب.", frappe.PermissionError)
	context.no_cache = 1
	context.user_full_name = frappe.utils.get_fullname(frappe.session.user)
