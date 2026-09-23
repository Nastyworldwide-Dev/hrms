"""Home read "2 attendance fixs to approve" (review of ad540b28c).

The app made a plural by adding "s" to the noun the server sent. English does
not work that way for "fix", and the server is the one place the wording
lives, so it sends both forms and the app picks one. Bench-free: the table is
read from the source.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "api" / "needs_you.py"


def _row_copy():
	tree = ast.parse(SOURCE.read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "ROW_COPY":
			return ast.literal_eval(node.value)
	raise AssertionError("ROW_COPY not found")


class TestEveryNounHasItsPlural(unittest.TestCase):
	def test_each_type_carries_one_and_many(self):
		for doctype, entry in _row_copy().items():
			self.assertEqual(len(entry), 3, f"{doctype}: (noun, plural, route)")

	def test_fix_is_fixes(self):
		self.assertEqual(_row_copy()["Attendance Request"][:2], ("attendance fix", "attendance fixes"))

	def test_the_row_sends_the_plural(self):
		self.assertIn('"nouns": nouns', SOURCE.read_text())


if __name__ == "__main__":
	unittest.main()
