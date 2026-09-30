CLASS: an app link offered only through broad roles, so a narrow need forces broad access
hrms/api/app_links.py:APP_ROLES same-root — Approva User added; the five existing roles unchanged
hrms/patches/v16_0/add_approva_user_role.py same-root — creates the role, no doctype permissions
frontend/src/data/appLinks.js not-affected — keeps the title and address only; shows what the server answers
Approva app (Nastyworldwide-Dev/Approva) not-affected — /approva and submit_request only require a login; approving needs Reporting Manager or being the named approver
