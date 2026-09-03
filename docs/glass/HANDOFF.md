# HANDOFF
prompt:   OT/Replacement-Leave engine — correct the calculation, make rules HR-configurable
status:   partial
commit:   b807e6be9 on nz-glass (3: b905197d OT calc, 3679dde5 RL ratio backend, b807e6be PWA labels)
files:    hrms/utils/ot_calculation.py (+ test) — OT = worked - shift length, late owed back
          hrms/hr/doctype/attendance/attendance.py — passes in_time so lateness applies
          hrms/hr/doctype/ot_request/ot_request.py (+ test) — replacement_leave_hours_per_day()
          hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py, hrms/api/__init__.py
          hrms/patches/v16_0/add_replacement_leave_hours_per_day_setting.py — HR Settings field
          frontend/src/{components/ReplacementLeaveCard,views/ot/ReplacementLeave,views/ot/ReplacementLeaveClaimForm}.vue
verify:   run-tests env-broken (orjson/py3.14); verified via bench console —
          OT table 9:30-6:30=0, 9:30-7:30=1h, 8:30-6:30=0.5h; RL ratio missing->8, set 6->6
flags:    OT calc now HR's rule (total worked - shift length, early ignored, late owed back).
          RL 8h=1day now HR-editable (HR Settings), fails open to 8. Entitlement = existing
          single tick (OT Pay OR Replacement Leave), no change needed. Payroll untouched.
next:     DONE this turn: OT brain (calc + config). TODO: PWA consolidation — one
          "Claim Overtime or Leave" button, remove the 2 Attendance rows + the redundant
          "1 day available" block on Leaves. Reuses _is_routed_approver (no new approver code).
