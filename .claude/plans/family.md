CLASS: the same request state named differently on two screens. Nadi says Waiting / Approved / Rejected / Cancelled (requestStatus.js, owner ruling 21 Sep); Desk showed Draft in red, Open or Pending, and "Draft" for a leave saved as Approved but never submitted (nothing happened: no balance moved, no attendance written, proven 5 Oct 2026). Someone using both (HR, a Shift Supervisor) read two words for one state.
hrms/public/js/request_status.bundle.js:indicator same-root (new: the one Desk rule, Waiting by docstatus 0 whatever the status says)
hrms/hr/doctype/leave_application/leave_application_list.js same-root (fixed here: calls the rule; it had its own Draft/Open map)
hrms/hr/doctype/ot_request/ot_request_list.js same-root (fixed here: keeps its 2-decimal formatter, adds the indicator)
hrms/hr/doctype/shift_request/shift_request_list.js same-root (fixed here: keeps its shift-tools button, adds the indicator)
hrms/hr/doctype/attendance_request/attendance_request_list.js same-root (new list script: the doctype had none)
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim_list.js same-root (new list script)
hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request_list.js same-root (new list script)
hrms/hr/doctype/expense_claim/expense_claim_list.js ticket desk-wording-expense-remote — two axes (approval + payment) and Frappe doctype "states" own its indicator; needs its own ruling on "Approved · unpaid" in Desk
hrms/hr/doctype/remote_checkin_request ticket desk-wording-expense-remote — not submittable (status is the whole truth, Pending vs Waiting), no list script yet
