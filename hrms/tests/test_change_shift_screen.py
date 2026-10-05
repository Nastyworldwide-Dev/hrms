"""HR's "Change shift from..." dialog is wired to the server it was built for.

The dialog (hrms/public/js/change_shift_from.bundle.js) must be loaded at boot,
call the one whitelisted endpoint, keep HR-only, and send the endpoint exactly
what it reads. A rename on either side would leave HR with a button that does
nothing and no test failing.

	PYTHONPATH=. python3 hrms/tests/test_change_shift_screen.py
"""

import ast
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
BUNDLE = (ROOT / "public/js/change_shift_from.bundle.js").read_text()
HOOKS = (ROOT / "hooks.py").read_text()
ROSTER = ROOT / "api/roster.py"

def _endpoint():
	tree = ast.parse(ROSTER.read_text())
	return next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "change_shift_from")

class TestChangeShiftScreen(unittest.TestCase):
	def test_it_is_loaded_at_boot(self):
		self.assertIn('"change_shift_from.bundle.js"', HOOKS)

	def test_it_calls_the_endpoint_that_exists(self):
		self.assertIn('"hrms.api.roster.change_shift_from"', BUNDLE)
		self.assertTrue(_endpoint())

	def test_it_sends_the_arguments_the_endpoint_takes(self):
		params = {a.arg for a in _endpoint().args.args}
		body = BUNDLE.split("args: {")[1].split("},")[0]
		for sent in re.findall(r"(\w+),?\s*(?::|\n)", body):
			if sent in ("employee", "start_date", "shifts"):
				self.assertIn(sent, params, sent)
		for needed in ("employee", "start_date", "shifts"):
			self.assertIn(needed, body)

	def test_it_posts_and_the_endpoint_is_post_only(self):
		self.assertIn('type: "POST"', BUNDLE)
		decorator = ast.unparse(_endpoint().decorator_list[0])
		self.assertIn("POST", decorator)

	def test_only_hr_sees_the_button_and_the_server_still_decides(self):
		self.assertIn('["HR User", "HR Manager"]', BUNDLE)
		self.assertIn("sees_all_employee_data", ast.unparse(_endpoint()))

	def test_the_weekday_names_match_what_the_server_accepts(self):
		from hrms.utils import shift_change

		names = re.search(r"CS_WEEKDAYS = \[(.*?)\]", BUNDLE).group(1)
		self.assertEqual(re.findall(r'"(\w+)"', names), list(shift_change.WEEKDAYS))

	def test_a_press_while_saving_does_nothing(self):
		self.assertIn("state.busy", BUNDLE)

if __name__ == "__main__":
	unittest.main()
