"""Unit tests for hrms.utils.team_status.derive_member_status.

Pure-logic tests — no Frappe DB needed. Run with:
    python -m unittest hrms.utils.test_team_status
"""

import unittest
from datetime import date, time

from hrms.utils.team_status import derive_member_status

TODAY = date(2026, 8, 12)


def status(**overrides):
	ctx = {
		"day": TODAY,
		"today": TODAY,
		"now_time": time(10, 0),
		"on_leave": None,
		"is_holiday": False,
		"attendance_status": None,
		"has_checkin": False,
		"shift_start": time(9, 0),
		"shift_end": time(18, 0),
	}
	ctx.update(overrides)
	return derive_member_status(**ctx)


class TestDeriveMemberStatus(unittest.TestCase):
	def test_punches_mean_present(self):
		self.assertEqual(status(has_checkin=True), "Present")

	def test_punches_beat_approved_leave(self):
		# someone who punched in despite approved leave is factually present
		self.assertEqual(status(has_checkin=True, on_leave={"leave_type": "Annual Leave"}), "Present")

	def test_present_attendance_without_checkin_counts(self):
		for att in ("Present", "Work From Home", "Half Day"):
			self.assertEqual(status(attendance_status=att), "Present")

	def test_approved_leave_shows_on_leave(self):
		self.assertEqual(status(on_leave={"leave_type": "Annual Leave"}), "On Leave")

	def test_holiday_without_punches_is_off(self):
		self.assertEqual(status(is_holiday=True), "Off")

	def test_future_day_is_scheduled(self):
		self.assertEqual(status(day=date(2026, 8, 13)), "Scheduled")

	def test_past_day_without_anything_is_absent(self):
		self.assertEqual(status(day=date(2026, 8, 11)), "Absent")

	def test_today_before_shift_end_is_not_in_yet(self):
		self.assertEqual(status(now_time=time(10, 0)), "Not In Yet")

	def test_today_after_shift_end_is_absent(self):
		self.assertEqual(status(now_time=time(18, 30)), "Absent")

	def test_today_without_shift_gives_benefit_of_doubt(self):
		self.assertEqual(status(shift_start=None, shift_end=None), "Not In Yet")

	def test_overnight_shift_never_flips_to_absent_same_day(self):
		# shift 21:00 -> 06:00 ends tomorrow; 23:00 today is still Not In Yet
		self.assertEqual(
			status(shift_start=time(21, 0), shift_end=time(6, 0), now_time=time(23, 0)),
			"Not In Yet",
		)


if __name__ == "__main__":
	unittest.main()
