# HANDOFF
prompt:   withdrawal (owner ruling "a"), geofence accuracy cliff
status:   done
commit:   3f510070e on nz-glass
files:    hrms/utils/approved_request_guard.py (may_cancel, _withdrawal_block)
          hrms/api/approval.py (finalize asks may_cancel)
          frontend/src/utils/cancelRule.js (server answers, not this file)
          hrms/utils/geofence.py + frontend/src/utils/geolocation.js
          frontend/src/components/{StrictRejection,RemoteCheckin}Dialog.vue
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_an_employee_can_withdraw_their_own_request.py hrms/tests/test_geofence_allowance_has_no_cliff.py
flags:    Employee withdrawal REVERSES the 14 Sep ruling (owner said "a").
          Money limits kept: paid OT, and days inside a submitted salary slip.
          UNVERIFIED: a leave encashment or carry-forward expiry landing
          BETWEEN approval and withdrawal — needs a bench check before anyone
          withdraws an old leave.
next:     Owner releases. Open: should strict geofence stay harsh on coarse
          readings specifically (today it keeps the same 250 m it always had).
