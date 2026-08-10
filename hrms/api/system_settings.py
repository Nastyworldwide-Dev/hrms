import frappe


@frappe.whitelist(allow_guest=True)
def get_user_pass_login_disabled():
	return frappe.get_system_settings("disable_user_pass_login")


@frappe.whitelist()
def get_timezones() -> list[str]:
	"""Timezone list for the attendance-timezone pickers on Shift Location and
	Company. Frappe's own loader (system_settings.load) is System Manager-only,
	but HR Managers need to set these."""
	from frappe.utils.momentjs import get_all_timezones

	return get_all_timezones()
