# Family — fix(approval): decision field is the approver's (21 Sep 2026)
CLASS: a request's decision field was fenced on the decision PATH (decide/finalize) and on the employee field, never on the field itself — read_only trusted as a server rule
Changed symbol: `validate` in the NEW module hrms/utils/decision_field_guard.py (a doc_events hook). The machine matched every `validate` in the app; none of them call this module — they are other doctypes' own validate methods.
hrms/api/hr_contacts.py:24 not-affected — comment about HR Contact's own validate
hrms/api/kpi.py:523 not-affected — comment about KPI validate
hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request.py:120 not-affected — Leave Allocation.validate(), not a request decision field
hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request.py:157 not-affected — Leave Allocation.validate()
hrms/hr/doctype/employee_instant_feedback/employee_instant_feedback.py:75 not-affected — comment, own validate
hrms/hr/doctype/employee_onboarding/employee_onboarding.py:19 not-affected — super().validate() of Employee Onboarding, not in DECIDE_THEN_SUBMIT
hrms/hr/doctype/employee_one_on_one/employee_one_on_one.py:87 not-affected — comment, own validate
hrms/hr/doctype/employee_separation/employee_separation.py:10 not-affected — super().validate(), not a request
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:130 not-affected — Leave Allocation.validate()
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:148 not-affected — comment about allocation validate
hrms/hr/doctype/shift_swap_request/shift_swap_request.py:192 not-affected — comment, own validate; Shift Swap Request is not in DECIDE_THEN_SUBMIT
hrms/hr/utils.py:720 not-affected — Leave Allocation.validate()
hrms/overrides/shift_assignment_hooks.py:33 not-affected — docstring about Shift Assignment validate
hrms/patches/v15_91_1/seed_last_sync_for_auto_update_shifts.py:7 not-affected — docstring about ShiftType.validate
hrms/sync/checkin_recovery.py:450 not-affected — comment about Employee Checkin validate
Same-root, fixed here: every doctype in DECIDE_THEN_SUBMIT (wired in hooks.py; test_decision_field_guard pins the set). Remote Checkin Request already guards its own field in before_save.
