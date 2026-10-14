# HANDOFF
prompt:   receipts, mileage, time slips (14 Oct)
status:   done
commit:   bff289765 on nz-glass (tag v2.0.0-alpha.48)
files:    hrms/hr/doctype/expense_claim/expense_claim.py (mileage pricing)
          hrms/hr/doctype/attendance_request/attendance_request.py (time slip)
          hrms/hr/doctype/employee_checkin/employee_checkin.py (excused_late guard)
          hrms/api/now.py, hrms/api/needs_you.py, hrms/api/approvals_list.py
          frontend/src/components/CheckInPanel.vue, NowBar.vue, TimeSlipFields.vue
          frontend/src/components/ExpensesTable.vue, views/expense_claim/Form.vue
          hrms/patches/v16_0/add_time_slip_reason.py
verify:   python3 hrms/tests/test_time_slip.py && python3 hrms/tests/test_expense_mileage.py
flags:    migrate needed. HR: Rate per km on mileage types; untick Receipt Required where not needed. Deferred: file-row tick, night-shift sheet hint.
next:     deploy alpha.45-48 with migrate; HR setup; watch first real time slips
