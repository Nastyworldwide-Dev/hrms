# FAMILY — a money check aimed at a field that is not the period

CLASS: a per-doctype map whose entries are validated for EXISTENCE and not for
MEANING. `REQUEST_PERIOD_FIELDS["Travel Request"]` was `("creation",)` —
Frappe's row-save timestamp, not any travel date. A trip filed after its pay
period would have compared TODAY against that payslip, found no overlap, and
let the employee withdraw something already paid. The test that was supposed to
catch this asked "is the doctype listed", and it was.

Found by the review of 96962182a.

ROOT CAUSE: the entry. Travel Request's dates live on its itinerary child
table, so it is now absent from the map on purpose, and absence REFUSES the
employee instead of waving them through — "I cannot check" and "it is not
paid" must never look the same from inside this guard.

## Every entry, checked against the doctype's own JSON

hrms/utils/approved_request_guard.py:66 (Travel Request) — same-root (fixed here)
  Removed, with the reason written where the next person will look.
hrms/utils/approved_request_guard.py::_withdrawal_block — same-root (fixed here)
  Was `_slip_covering`, returning a slip name. It returns the SENTENCE now, so
  the three cases (unreadable doctype, no dates on the row, genuinely paid) say
  three different things to the employee instead of one borrowed one.
hrms/tests/…::test_every_named_field_exists_on_its_doctype — same-root (added here)
  Reads each doctype's JSON and fails if a named field is not a Date or
  Datetime on it. This is the test that would have caught `creation`.
hrms/tests/…::test_every_decidable_doctype_is_answered_one_way_or_the_other
  — same-root (amended here)
  Was "every decidable doctype must be in the map". A doctype may be absent on
  purpose now, as long as absence refuses.
Leave Application (from_date, to_date), Expense Claim (posting_date),
Shift Request (from_date, to_date), Attendance Request (from_date, to_date),
OT Request (ot_date), Replacement Leave Claim (bank_month),
Compensatory Leave Request (work_from_date, work_end_date),
Employee Advance (posting_date) — not-affected
  Each verified against its own doctype JSON by the new test, not by eye.
