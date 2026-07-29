import frappe
from frappe.tests.utils import FrappeTestCase

from talab.roles import TALAB_ROLES


class TestTalabFoundation(FrappeTestCase):
	def test_required_roles_are_installed(self):
		for role_name in TALAB_ROLES:
			self.assertTrue(frappe.db.exists("Role", role_name))
