import uuid

import frappe
from frappe import _
from frappe.model.document import Document


class TalabOperationRequest(Document):
	def before_insert(self):
		if not self.flags.from_talab_api:
			frappe.throw(_("Operation requests can only be created by the Talab portal."), frappe.PermissionError)
		self.requested_by = frappe.session.user
		self.status = "Processing"
		self._validate_request_id()

	def validate(self):
		if not self.flags.from_talab_api:
			frappe.throw(_("Operation requests can only be changed by the Talab portal."), frappe.PermissionError)
		self._validate_request_id()

	def _validate_request_id(self):
		try:
			value = uuid.UUID(str(self.request_id))
		except (TypeError, ValueError, AttributeError):
			frappe.throw(_("A valid operation request ID is required."), frappe.ValidationError)
		if value.version != 4 or str(value) != str(self.request_id).lower():
			frappe.throw(_("A valid operation request ID is required."), frappe.ValidationError)
