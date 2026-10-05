CLASS: a pill whose click-through filter names a different word from the one it shows, so the filter misses rows the pill describes. The "Approved · unpaid" pill filtered on the stored money word Unpaid, but an approved claim with nothing sanctioned keeps the stored status Submitted (set_status), so clicking the pill did not list it (design review of 3f761024f).
hrms/hr/doctype/expense_claim/expense_claim_list.js same-root (fixed here: the Approved · unpaid pill filters on approval_status = Approved)
hrms/hr/doctype/expense_claim/expense_claim_list.js:Paid / Rejected pills not-affected — their stored words (Paid, Rejected) are exactly the ones the filter names
hrms/public/js/request_status.bundle.js not-affected — filters on docstatus or the decision word, both stored as shown
hrms/hr/doctype/remote_checkin_request/remote_checkin_request_list.js not-affected — Waiting filters on the stored Pending
