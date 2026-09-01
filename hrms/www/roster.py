import frappe

# The page embeds a per-session CSRF token; without no_cache the website page
# cache can serve one user's cached HTML (and token) to another, breaking every
# roster POST. hrms.py (the PWA shell) already sets this — roster must match.
no_cache = 1


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	frappe.db.commit()  # nosempgrep
	context = frappe._dict()
	context.csrf_token = csrf_token
	return context
