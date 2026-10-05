CLASS: the same request state named differently on two screens (see 0d1bfd039). Remote Checkin Request is not submittable, so Desk showed its stored word Pending while Nadi says Waiting.
hrms/hr/doctype/remote_checkin_request/remote_checkin_request_list.js same-root (new list script: Pending shows as Waiting in orange; the click filter still uses the stored word)
hrms/public/js/request_status.bundle.js not-affected — that rule reads docstatus, which this doctype does not have; it has its own three-line rule here
hrms/hr/doctype/expense_claim/expense_claim_list.js ticket desk-wording-expense-remote — next commit: Frappe draws its status from the doctype's states before any list script
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.json not-affected — the stored options (Pending / Approved / Rejected) are unchanged
frontend/src/utils/requestStatus.js not-affected — Nadi already maps Pending to Waiting
