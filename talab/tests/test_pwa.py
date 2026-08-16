import json
import struct
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase


class TestTalabPWA(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.app = Path(frappe.get_app_path("talab"))

	def test_manifest_is_valid_and_scoped_to_talab(self):
		manifest = json.loads((self.app / "public/manifest.webmanifest").read_text())
		self.assertEqual(manifest["start_url"], "/talab")
		self.assertEqual(manifest["scope"], "/talab")
		self.assertEqual((manifest["lang"], manifest["dir"], manifest["display"]), ("ar", "rtl", "standalone"))

	def test_required_png_icons_exist_at_declared_sizes(self):
		for filename, expected in (("talab-192.png", (192, 192)), ("talab-512.png", (512, 512)), ("talab-maskable-512.png", (512, 512)), ("talab-apple-180.png", (180, 180))):
			path = self.app / "public/icons" / filename
			self.assertTrue(path.is_file())
			with path.open("rb") as icon:
				self.assertEqual(icon.read(8), b"\x89PNG\r\n\x1a\n")
				length = struct.unpack(">I", icon.read(4))[0]
				self.assertEqual(icon.read(4), b"IHDR")
				self.assertEqual(struct.unpack(">II", icon.read(length)[:8]), expected)

	def test_service_worker_is_network_only_for_apis_and_writes(self):
		worker = (self.app / "www/talab-sw.js").read_text()
		self.assertIn('request.method !== "GET"', worker)
		self.assertIn('url.pathname.startsWith("/api/")', worker)
		self.assertNotIn('addEventListener("sync"', worker)
		self.assertNotIn("indexedDB", worker)
		self.assertNotIn("/api/method", worker)

	def test_cache_allowlist_contains_only_safe_shell_assets(self):
		worker = (self.app / "www/talab-sw.js").read_text()
		for forbidden in ("dashboard_summary", "mill_statuses", "customers", "open_shifts", "shift_details", "payment_reference", "csrf"):
			self.assertNotIn(forbidden, worker)
		for required in ("mobile_portal.css", "mobile_portal.js", "offline.html", "talab-192.png", "talab-512.png"):
			self.assertIn(required, worker)

	def test_logout_clears_talab_session_state(self):
		script = (self.app / "public/js/mobile_portal.js").read_text()
		self.assertIn('key.startsWith("talab.")', script)
		self.assertNotIn("localStorage", script)
