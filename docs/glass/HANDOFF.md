# HANDOFF
prompt:   PWA polish — empty dropdowns (permission bug) sweep + expense claim cleanup
status:   done, pushed. Frontend suite 135/135.
commit:   8cf19e19d on nz-glass (chain: 7e0335ff5, c9cac8192, 8cf19e19d)
files:    hrms/api/__init__.py — get_shift_types (fenced supplier)
          frontend/src/components/ExpensesTable.vue — expense_type documentList
          frontend/src/data/attendance.js — shiftTypes resource
          frontend/src/views/attendance/ShiftRequestForm.vue — shift_type documentList
          frontend/src/views/attendance/AttendanceRequestForm.vue — shift documentList
          frontend/src/views/expense_claim/Form.vue — hide cost_center/payable_account/project
verify:   yarn --cwd frontend test (135/135). Manual: as a NON-HR employee, open
          Request a Shift -> shift dropdown populates; New Expense Claim -> type
          populates, no cost-center/account/project clutter.
finding:  Root cause = raw Link fields search via frappe.desk.search.search_link,
          which needs Desk read perm on the target master; a bare Employee has none
          -> empty picker. Fix = feed a fenced get_* list as documentList. Sweep
          caught a CRITICAL the agent missed: shift_type on Shift Request (employees
          couldn't request a shift at all). Desk side unaffected (HR has permission).
flags:    Memory nadi-empty-dropdowns corrected: NOT all empty dropdowns are config.
next:     Nabil's raw notes backlog (notification doctype-error bug, RL public-holiday,
          self-claim eligibility, announcement popup, expense GL by company). Await pick.
