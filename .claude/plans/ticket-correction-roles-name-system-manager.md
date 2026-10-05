# Ticket: correction_cancel names System Manager (5 Oct 2026)
hrms/utils/approved_request_guard.py CORRECTION_ROLES = {"HR Manager", "System Manager"} lets a System Manager call
hrms.api.correction_cancel.cancel_for_correction. Found while fixing the check-in System Manager hole (family hunt).
Not reachable by an admin-only login today: the endpoint then runs _request_read_allowed, which refuses a System Manager
who holds no HR role. Owner to say: may an admin-only login correct requests? If NOT, drop System Manager from
CORRECTION_ROLES and from the error text. Not changed here: it is a rule change nobody asked for yet.
