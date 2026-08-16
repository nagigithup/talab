import uuid
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from talab import mobile_api


class TestTalabMobileAPI(FrappeTestCase):
	customer = "Talab Mobile API Customer"
	operator = "talab.operator@example.com"
	other_operator = "talab.operator.two@example.com"
	custodian = "talab.custodian@example.com"
	reviewer = "talab.reviewer@example.com"
	unauthorized = "talab.basic@example.com"

	def setUp(self):
		frappe.set_user("Administrator")
		self._clean_shifts()
		for mill in ("1", "2", "3"):
			frappe.db.set_value("Talab Mill", mill, {"enabled": 1, "current_status": "Available", "current_open_shift": None})
		settings = frappe.get_single("Talab Settings")
		settings.update({"default_shift_rental_amount": 40, "default_mercury_issue_qty": 200, "default_mercury_exemption_qty": 10, "mercury_price_per_gram": 2, "enable_additional_charges": 0})
		settings.save(ignore_permissions=True)
		self._ensure_customer()
		self._ensure_user(self.operator, "Mill Operator")
		self._ensure_user(self.other_operator, "Mill Operator")
		self._ensure_user(self.custodian, "Mercury Custodian")
		self._ensure_user(self.reviewer, "Accounts Reviewer")
		self._ensure_user(self.unauthorized)

	def tearDown(self):
		frappe.set_user("Administrator")
		self._clean_shifts()
		for mill in ("1", "2", "3"):
			frappe.db.set_value("Talab Mill", mill, {"enabled": 1, "current_status": "Available", "current_open_shift": None})

	def _ensure_user(self, email, *roles):
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "Talab Test", "send_welcome_email": 0, "user_type": "System User"}).insert(ignore_permissions=True)
		user = frappe.get_doc("User", email)
		existing = {row.role for row in user.roles}
		for role in roles:
			if role not in existing:
				user.append("roles", {"role": role})
		user.save(ignore_permissions=True)

	def _ensure_customer(self):
		if frappe.db.exists("Customer", self.customer):
			return
		frappe.get_doc({
			"doctype": "Customer", "customer_name": self.customer, "customer_type": "Individual",
			"customer_group": frappe.db.get_value("Customer Group", {"is_group": 0}, "name"),
			"territory": frappe.db.get_value("Territory", {"is_group": 0}, "name"), "mobile_no": "0912345678",
		}).insert(ignore_permissions=True)

	def _clean_shifts(self):
		for name in frappe.get_all("Talab Mill Shift", filters={"customer": self.customer}, pluck="name"):
			frappe.db.delete("Talab Operation Request", {"result_document": name})
			doc = frappe.get_doc("Talab Mill Shift", name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc("Talab Mill Shift", name, force=True, ignore_permissions=True)

	def _open(self, mill="1"):
		frappe.set_user(self.operator)
		return mobile_api.create_shift(mill, self.customer, request_id=str(uuid.uuid4()))["result"]

	def _close(self, name, **values):
		frappe.set_user(self.custodian)
		return mobile_api.close_shift(name, mercury_returned=values.pop("mercury_returned", 190), request_id=str(uuid.uuid4()), payment_method=values.pop("payment_method", "Cash"), **values)["result"]

	def test_guest_cannot_access_mobile_apis(self):
		frappe.set_user("Guest")
		for method in (mobile_api.ping, mobile_api.dashboard_summary, mobile_api.mill_statuses, mobile_api.open_shifts, mobile_api.daily_summary):
			with self.assertRaises(frappe.PermissionError):
				method()

	def test_unauthorized_user_cannot_open_shift(self):
		frappe.set_user(self.unauthorized)
		with self.assertRaises(frappe.PermissionError):
			mobile_api.create_shift("1", self.customer, request_id=str(uuid.uuid4()))

	def test_authorized_open_uses_settings_and_prevents_duplicates(self):
		shift = self._open()
		self.assertEqual((shift["mercury_issued"], shift["mercury_exemption"], shift["mercury_price_per_gram"], shift["shift_rental_amount"]), (200, 10, 2, 40))
		self.assertEqual(frappe.db.get_value("Talab Mill", "1", "current_status"), "Operating")
		with self.assertRaises(frappe.ValidationError):
			mobile_api.create_shift("1", self.customer, request_id=str(uuid.uuid4()))

	def test_unavailable_mill_cannot_be_opened(self):
		frappe.db.set_value("Talab Mill", "1", "current_status", "Maintenance")
		with self.assertRaises(frappe.ValidationError):
			self._open()

	def test_close_submits_recalculates_and_releases_mill(self):
		shift = self._open()
		closed = self._close(shift["name"], mercury_returned=170, amount_paid=50)
		self.assertEqual((closed["docstatus"], closed["shift_status"]), (1, "Closed"))
		self.assertEqual((closed["mercury_shortage"], closed["chargeable_mercury"], closed["mercury_charge"], closed["total_due"]), (30, 20, 40, 80))
		self.assertEqual((closed["amount_paid"], closed["outstanding_amount"], closed["payment_status"]), (50, 30, "Partially Paid"))
		self.assertEqual(frappe.db.get_value("Talab Mill", "1", ["current_status", "current_open_shift"]), ("Available", None))

	def test_repeated_close_is_rejected(self):
		shift = self._open()
		self._close(shift["name"])
		with self.assertRaises(frappe.ValidationError):
			self._close(shift["name"])

	def test_bank_transfer_requires_reference_but_cash_does_not(self):
		bank = self._open("1")
		with self.assertRaises(frappe.ValidationError):
			self._close(bank["name"], payment_method="Bank Transfer", amount_paid=40)
		self._close(bank["name"], payment_method="Bank Transfer", payment_reference="BANK-1", amount_paid=40)
		cash = self._open("2")
		closed = self._close(cash["name"], payment_method="Cash", amount_paid=40)
		self.assertEqual(closed["payment_method"], "Cash")

	def test_paid_above_total_is_rejected(self):
		shift = self._open()
		with self.assertRaises(frappe.ValidationError):
			self._close(shift["name"], mercury_returned=200, amount_paid=41)

	def test_calculated_fields_cannot_be_supplied_to_close_api(self):
		shift = self._open()
		frappe.set_user(self.custodian)
		with self.assertRaises(TypeError):
			mobile_api.close_shift(shift["name"], mercury_returned=200, request_id=str(uuid.uuid4()), payment_method="Cash", total_due=1)

	def test_daily_summary_and_accounts_reviewer_are_read_only(self):
		first = self._open("1")
		self._close(first["name"], mercury_returned=200, amount_paid=40)
		second = self._open("2")
		frappe.set_user(self.reviewer)
		summary = mobile_api.daily_summary()
		self.assertEqual((summary["total_shifts"], summary["open_shifts"], summary["closed_shifts"]), (2, 1, 1))
		self.assertEqual((summary["total_due"], summary["total_paid"], summary["total_outstanding"]), (80, 40, 40))
		with self.assertRaises(frappe.PermissionError):
			mobile_api.create_shift("3", self.customer, request_id=str(uuid.uuid4()))
		with self.assertRaises(frappe.PermissionError):
			mobile_api.close_shift(second["name"], mercury_returned=200, request_id=str(uuid.uuid4()), payment_method="Cash")

	def test_route_files_and_assets_exist(self):
		app = Path(frappe.get_app_path("talab"))
		for relative in ("www/talab.py", "www/talab.html", "public/js/mobile_portal.js", "public/css/mobile_portal.css"):
			self.assertTrue((app / relative).is_file())

	def test_transaction_apis_require_valid_request_ids(self):
		frappe.set_user(self.operator)
		for request_id in (None, "", "not-a-uuid", str(uuid.uuid1())):
			with self.assertRaises(frappe.ValidationError):
				mobile_api.create_shift("1", self.customer, request_id=request_id)

	def test_reusing_open_request_returns_original_shift(self):
		request_id = str(uuid.uuid4())
		frappe.set_user(self.operator)
		first = mobile_api.create_shift("1", self.customer, request_id=request_id)
		second = mobile_api.create_shift("1", self.customer, request_id=request_id)
		self.assertEqual(first["result"]["name"], second["result"]["name"])
		self.assertEqual(frappe.db.count("Talab Mill Shift", {"customer": self.customer, "mill": "1"}), 1)
		with self.assertRaises(frappe.ValidationError):
			mobile_api.create_shift("2", self.customer, request_id=request_id)

	def test_reusing_close_request_submits_only_once(self):
		shift = self._open()
		request_id = str(uuid.uuid4())
		frappe.set_user(self.custodian)
		first = mobile_api.close_shift(shift["name"], 200, request_id=request_id, payment_method="Cash", amount_paid=40)
		second = mobile_api.close_shift(shift["name"], 200, request_id=request_id, payment_method="Cash", amount_paid=40)
		self.assertEqual(first["result"]["name"], second["result"]["name"])
		self.assertEqual(second["result"]["docstatus"], 1)

	def test_operation_status_is_private_to_request_owner(self):
		request_id = str(uuid.uuid4())
		frappe.set_user(self.operator)
		opened = mobile_api.create_shift("1", self.customer, request_id=request_id)
		status = mobile_api.operation_status(request_id)
		self.assertEqual(status["result"]["name"], opened["result"]["name"])
		frappe.set_user(self.other_operator)
		with self.assertRaises(frappe.PermissionError):
			mobile_api.operation_status(request_id)

	def test_unknown_operation_status_returns_no_transaction_data(self):
		frappe.set_user(self.operator)
		request_id = str(uuid.uuid4())
		self.assertEqual(mobile_api.operation_status(request_id), {"request_id": request_id, "status": "Not Found"})
