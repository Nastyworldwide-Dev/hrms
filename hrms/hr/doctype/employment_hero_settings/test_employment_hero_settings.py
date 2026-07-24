# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import base64
import hashlib

from frappe.tests.utils import FrappeTestCase

from hrms.hr.doctype.employment_hero_settings.employment_hero_settings import _generate_pkce_pair


class TestEmploymentHeroSettings(FrappeTestCase):
	def test_pkce_pair_is_valid_s256(self):
		verifier, challenge = _generate_pkce_pair()
		# RFC 7636: challenge = base64url(sha256(verifier)) with no padding
		expected = (
			base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
			.decode("ascii")
			.rstrip("=")
		)
		self.assertEqual(challenge, expected)
		self.assertNotIn("=", verifier)
		self.assertNotIn("=", challenge)
		# code_verifier length must be 43..128 chars
		self.assertGreaterEqual(len(verifier), 43)
		self.assertLessEqual(len(verifier), 128)

	def test_pkce_pairs_are_unique(self):
		self.assertNotEqual(_generate_pkce_pair()[0], _generate_pkce_pair()[0])
