CLASS: a field added to a doctype does not reach a user's saved Report view (per-user column list in __UserSettings)

Instance: HR, 25 Sep 2026 — Day Type / OT Rate added (7c02c1d2b) but not visible as columns in HR's existing OT Request report; a "Day Type" filter box appeared in the top bar instead (in_standard_filter), which read as something added on top of the report.

Sites:
- OT Request Report view — same-root (patch inserts the two columns after Compensation in every saved view; the filter box removed)
- OT Request List view — not-affected: in_list_view already shows them
- other doctypes that gained fields this month — not-affected by this report (no HR report view asked for); the helper add_report_columns is reusable

Locked: hrms/utils/test_report_columns.py (4). Bench: a saved view gains the two columns after Compensation, nothing else moves.
