CLASS: a safety check that runs only when the caller remembers to ask for it. decide() and finalize() compared the request's revision with the one the approver read ONLY when the caller passed it; a caller that left it out skipped the check, so a request edited after the approver read it could be approved unseen.
hrms/api/approval.py:_check_review_revision same-root (fixed here: `required` refuses a missing or empty revision before any write)
hrms/api/approval.py:decide same-root (passes required=True)
hrms/api/approval.py:finalize same-root (passes required=True)
hrms/api/approval.py:decide_many not-affected — _bulk_items already refuses a row without a revision up front, now noted
hrms/api/correction_cancel.py:cancel_for_correction not-affected — HR's correction tool keeps the optional check by design
frontend/src/components/RequestActionSheet.vue not-affected — sends expected_modified (currentRequest)
frontend/src/components/FormView.vue not-affected — sends expected_modified to finalize
hrms/public/js/utils/request_approval.js not-affected — sends expected_modified (Desk test 3/3)
hrms/public/js/utils/approved_request_cancel.js not-affected — sends expected_modified
