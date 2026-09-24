CLASS: Desk setup a Nadi request depends on, with no readiness finding (the request fails for staff first)

Instance: on the test site each of these broke a request an employee filed correctly (alpha.6 journey, 24 Sep 2026): no expense account for the company, no Default Expense Claim Payable Account, no active Leave Period, shift overtime off.

Checks in hrms/utils/readiness.py evaluate():
- expense_types (company with NO usable type) — same-root (new). A single type without an account is not reported: Nadi already hides it (api.configured_expense_claim_types)
- expense_payable — same-root (new)
- leave_period — same-root (new)
- shift_overtime (WARN: a choice) — same-root (new)
- holiday calendar, leave allocation — not-affected: already reported
- approver chain / login — not-affected: Request Access Health report covers them
Also: the geofence block RETURNS EARLY when geolocation is off; the new checks sit before it (locked by test_reported_even_when_geolocation_is_off).

Locked: hrms/utils/test_readiness.py TestNadiRequestsCannotFail (5). Live on fresh.local: all four fire for the companies/shifts actually missing setup.
