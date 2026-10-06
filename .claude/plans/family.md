CLASS: one list of request types written twice. request_counts carried its own hand list of request doctypes beside approval.DECIDE_THEN_SUBMIT; Compensatory Leave Request was in one and not the other, so the employee's Requests chips (all / waiting / approved / rejected) never counted it.
hrms/api/request_counts.py:DECISION_FIELD same-root (fixed here: derived from approval.DECIDE_THEN_SUBMIT, field = first of the pair)
hrms/api/approval.py:DECIDE_THEN_SUBMIT not-affected — the one list, unchanged
frontend/src/utils/requestStatus.js:REQUEST_TYPES ticket one-request-type-list — the app's own copy of the same list (it does list Compensatory Leave Request, checked); a third copy, kept by hand
hrms/api/approvals_list.py:KIND not-affected — labels per doctype for the approver screen, already includes Compensatory Leave Request
