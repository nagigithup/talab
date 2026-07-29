import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime, today


class TestTalabMillShift(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		settings = frappe.get_single("Talab Settings")
		settings.update({"default_shift_rental_amount": 40, "default_mercury_issue_qty": 200, "default_mercury_exemption_qty": 10, "mercury_price_per_gram": 2})
		settings.save(ignore_permissions=True)
		self.customer = self._customer()

	def tearDown(self):
		for name in frappe.get_all("Talab Mill Shift", filters={"customer": self.customer}, pluck="name"):
			doc = frappe.get_doc("Talab Mill Shift", name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Talab Mill Shift", name, force=1, ignore_permissions=True)
		frappe.delete_doc("Customer", self.customer, force=1, ignore_permissions=True)

	def _customer(self):
		name = "Talab Test Customer"
		if not frappe.db.exists("Customer", name):
			customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
			territory = frappe.db.get_value("Territory", {"is_group": 0}, "name")
			frappe.get_doc(
				{
					"doctype": "Customer",
					"customer_name": name,
					"customer_group": customer_group,
					"territory": territory,
					"customer_type": "Individual",
				}
			).insert(ignore_permissions=True)
		return name

	def _shift(self, mill="1", returned=None, **values):
		doc = frappe.get_doc({"doctype": "Talab Mill Shift", "mill": mill, "customer": self.customer, "opening_datetime": now_datetime(), "mercury_returned": returned, **values})
		doc.insert(ignore_permissions=True)
		return doc

	def _close(self, shift, returned):
		shift.mercury_returned = returned
		shift.closing_datetime = add_to_date(shift.opening_datetime, minutes=30)
		shift.submit()
		return shift

	def test_mercury_calculations(self):
		shift = self._shift(returned=170, mercury_shortage=999, total_due=999)
		self.assertEqual((shift.mercury_shortage, shift.chargeable_mercury), (30, 20))
		self.assertEqual(shift.mercury_charge, 40)
		self.assertEqual(shift.total_due, 80)

	def test_exemption_and_full_return(self):
		self.assertEqual(self._shift(returned=195).chargeable_mercury, 0)
		self.assertEqual(self._shift(mill="2", returned=200).chargeable_mercury, 0)

	def test_invalid_return_values_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._shift(returned=201)
		with self.assertRaises(frappe.ValidationError):
			self._shift(returned=-1)

	def test_open_shift_rules(self):
		first = self._shift()
		with self.assertRaises(frappe.ValidationError):
			self._shift()
		self._close(first, 200)
		self._shift()
		self._shift(mill="2")

	def test_historical_prices_and_payment_status(self):
		shift = self._shift(returned=170, amount_paid=45)
		self.assertEqual((shift.total_due, shift.outstanding_amount, shift.payment_status), (80, 35, "Partially Paid"))
		settings = frappe.get_single("Talab Settings")
		settings.mercury_price_per_gram = 9
		settings.save(ignore_permissions=True)
		shift.reload()
		self.assertEqual(shift.mercury_price_per_gram, 2)

	def test_mills_are_seeded_without_duplicates(self):
		self.assertEqual(frappe.db.count("Talab Mill"), 15)

	def test_settings_and_calculated_fields_are_protected_by_metadata(self):
		settings_roles = {row.role for row in frappe.get_meta("Talab Settings").permissions}
		self.assertEqual(settings_roles, {"Talab System Manager", "Talab Manager"})
		for fieldname in ("mercury_shortage", "chargeable_mercury", "mercury_charge", "total_due", "outstanding_amount"):
			field = frappe.get_meta("Talab Mill Shift").get_field(fieldname)
			self.assertTrue(field.read_only)
			self.assertEqual(field.permlevel, 1)
