from decimal import Decimal

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, get_datetime, now_datetime, today

CALCULATED_FIELDS = ("mercury_shortage", "chargeable_mercury", "mercury_charge", "total_due", "outstanding_amount", "payment_status")
PAYMENT_FIELDS = {"amount_paid", "payment_method", "payment_reference", "notes"}
MANAGER_ROLES = {"Talab System Manager", "Talab Manager"}


class TalabMillShift(Document):
	def autoname(self):
		self.name = frappe.model.naming.make_autoname("TMS-.YYYY.-.#####")

	def before_insert(self):
		self.shift_date = self.shift_date or today()
		self.opening_datetime = self.opening_datetime or now_datetime()
		self.operator = self.operator or frappe.session.user
		self.shift_status = "Open"
		self._lock_mill_and_assign_shift_number()
		self._copy_opening_defaults()

	def validate(self):
		self._enforce_role_boundaries()
		self._calculate_values()
		self._validate_input()
		if self.shift_status == "Open":
			self._validate_open_mill()

	def before_submit(self):
		if frappe.session.user != "Administrator" and not (MANAGER_ROLES | {"Mercury Custodian"}).intersection(frappe.get_roles()):
			frappe.throw(_("Only a Mercury Custodian or Talab manager can close a shift."))
		self.shift_status = "Closed"
		self._validate_input()
		self._calculate_values()

	def on_submit(self):
		self._release_mill()

	def on_cancel(self):
		frappe.db.set_value("Talab Mill Shift", self.name, "shift_status", "Cancelled", update_modified=False)
		self._release_mill()

	def on_trash(self):
		self._release_mill()

	def _settings_value(self, fieldname, fallback):
		return frappe.db.get_single_value("Talab Settings", fieldname) or fallback

	def _copy_opening_defaults(self):
		self.shift_rental_amount = self.shift_rental_amount or self._settings_value("default_shift_rental_amount", 40)
		self.mercury_issued = self.mercury_issued or self._settings_value("default_mercury_issue_qty", 200)
		self.mercury_exemption = self.mercury_exemption or self._settings_value("default_mercury_exemption_qty", 10)
		self.mercury_price_per_gram = self.mercury_price_per_gram or self._settings_value("mercury_price_per_gram", 0)

	def _lock_mill_and_assign_shift_number(self):
		frappe.db.sql("SELECT name FROM `tabTalab Mill` WHERE name=%s FOR UPDATE", self.mill)
		if frappe.db.exists("Talab Mill Shift", {"mill": self.mill, "shift_status": "Open", "docstatus": 0}):
			frappe.throw(_("This mill already has an open shift."))
		last_number = frappe.db.sql(
			"SELECT MAX(shift_number) FROM `tabTalab Mill Shift` WHERE mill=%s AND shift_date=%s FOR UPDATE",
			(self.mill, self.shift_date),
		)[0][0]
		self.shift_number = cint(last_number) + 1

	def _validate_open_mill(self):
		mill = frappe.get_doc("Talab Mill", self.mill)
		if not mill.enabled or mill.current_status in ("Disabled", "Maintenance"):
			frappe.throw(_("A disabled or maintenance mill cannot open a shift."))
		if mill.current_open_shift and mill.current_open_shift != self.name:
			frappe.throw(_("This mill already has an open shift."))

	def _validate_input(self):
		if flt(self.mercury_issued) <= 0:
			frappe.throw(_("Mercury issued must be greater than zero."))
		if self.mercury_returned is not None and flt(self.mercury_returned) < 0:
			frappe.throw(_("Returned mercury cannot be negative."))
		if self.mercury_returned is not None and flt(self.mercury_returned) > flt(self.mercury_issued):
			frappe.throw(_("Returned mercury cannot exceed issued mercury."))
		if self.closing_datetime and get_datetime(self.closing_datetime) < get_datetime(self.opening_datetime):
			frappe.throw(_("Closing time cannot be before opening time."))
		if self.shift_status == "Closed" and (not self.closing_datetime or self.mercury_returned in (None, "")):
			frappe.throw(_("A closed shift requires closing time and returned mercury."))
		if flt(self.amount_paid) < 0 or flt(self.amount_paid) > flt(self.total_due):
			frappe.throw(_("Amount paid must be between zero and total due."))
		if self.payment_method == "Bank Transfer" and not self.payment_reference:
			frappe.throw(_("Payment reference is mandatory for bank transfers."))

	def _calculate_values(self):
		issued, returned, exemption = (Decimal(str(flt(value))) for value in (self.mercury_issued, self.mercury_returned, self.mercury_exemption))
		shortage = max(issued - returned, Decimal("0"))
		chargeable = max(shortage - exemption, Decimal("0"))
		charge = chargeable * Decimal(str(flt(self.mercury_price_per_gram)))
		total = Decimal(str(flt(self.shift_rental_amount))) + charge + Decimal(str(flt(self.additional_charges)))
		paid = Decimal(str(flt(self.amount_paid)))
		self.mercury_shortage, self.chargeable_mercury, self.mercury_charge = float(shortage), float(chargeable), float(charge)
		self.total_due, self.outstanding_amount = float(total), float(total - paid)
		self.payment_status = "Paid" if paid == total and total else "Partially Paid" if paid else "Unpaid"

	def _enforce_role_boundaries(self):
		old = self.get_doc_before_save()
		if old and old.docstatus == 1:
			changed = {field for field in self.as_dict() if self.get(field) != old.get(field)}
			if changed - PAYMENT_FIELDS - set(CALCULATED_FIELDS) - {"modified", "modified_by"}:
				frappe.throw(_("Closed shift details cannot be changed."))
		if "Cashier" in frappe.get_roles() and not MANAGER_ROLES.intersection(frappe.get_roles()):
			if not old or old.docstatus != 1:
				frappe.throw(_("Cashiers can update payment fields only after a shift is closed."))

	def _release_mill(self):
		if not self.mill:
			return
		mill = frappe.get_doc("Talab Mill", self.mill)
		if mill.current_open_shift == self.name:
			mill.current_open_shift = None
			mill.current_status = "Available" if mill.enabled else "Disabled"
			mill.save(ignore_permissions=True)

	def after_insert(self):
		frappe.db.set_value("Talab Mill", self.mill, {"current_status": "Operating", "current_open_shift": self.name}, update_modified=False)
