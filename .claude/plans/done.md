GOAL: no Desk write endpoint in hrms can be triggered by a GET (CSRF skipped); the device ingestion endpoint is the one named exception.
DONE WHEN: 15 functions methods=["POST"]; test_desk_writes_are_post_only walks every whitelisted writer outside hrms/api.
CHECK: PYTHONPATH=. python3 hrms/tests/test_desk_writes_are_post_only.py; bench frappe.handler.is_valid_http_method: GET refused / POST allowed on update_status, send_exit_questionnaire, expire_allocation
