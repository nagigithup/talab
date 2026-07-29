import frappe

login_required = True
no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.user_full_name = frappe.utils.get_fullname(frappe.session.user)
