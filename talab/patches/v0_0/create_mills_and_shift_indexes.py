import frappe


def execute():
	if not frappe.db.exists("DocType", "Talab Mill"):
		return
	for mill_number in range(1, 16):
		if not frappe.db.exists("Talab Mill", {"mill_number": mill_number}):
			frappe.get_doc(
				{
					"doctype": "Talab Mill",
					"mill_number": mill_number,
					"mill_name": f"طاحونة رقم {mill_number}",
					"enabled": 1,
					"current_status": "Available",
				}
			).insert(ignore_permissions=True)
	if frappe.db.exists("DocType", "Talab Mill Shift"):
		frappe.db.add_unique("Talab Mill Shift", ("mill", "shift_date", "shift_number"), "unique_mill_date_shift")
