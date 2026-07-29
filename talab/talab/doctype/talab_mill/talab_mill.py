import frappe
from frappe import _
from frappe.model.document import Document


class TalabMill(Document):
	def validate(self):
		if not 1 <= int(self.mill_number or 0) <= 15:
			frappe.throw(_("Mill number must be between 1 and 15."))
		self.mill_name = f"طاحونة رقم {self.mill_number}"
		if frappe.db.exists("Talab Mill", {"mill_number": self.mill_number, "name": ["!=", self.name]}):
			frappe.throw(_("Mill number must be unique."))
		if not self.enabled:
			if self.current_open_shift:
				frappe.throw(_("A mill with an open shift cannot be disabled."))
			self.current_status = "Disabled"
