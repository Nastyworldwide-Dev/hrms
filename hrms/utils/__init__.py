from collections.abc import Generator

try:
	import requests
except ImportError:  # pragma: no cover — pure unit tests outside bench
	requests = None

try:
	import frappe
	from frappe.utils import add_days, date_diff
except ImportError:  # pragma: no cover — pure unit tests outside bench
	import types as _types

	frappe = _types.SimpleNamespace(
		whitelist=lambda *a, **kw: lambda fn: fn,
	)

	def add_days(date, days):
		from datetime import datetime, timedelta

		base = datetime.fromisoformat(date) if isinstance(date, str) else date
		return (base + timedelta(days=days)).date().isoformat()

	def date_diff(end, start):
		from datetime import datetime

		s = datetime.fromisoformat(start) if isinstance(start, str) else start
		e = datetime.fromisoformat(end) if isinstance(end, str) else end
		return (e - s).days


country_info = {}


# NOT whitelisted: this was a guest-reachable endpoint whose body makes an
# un-timed outbound request to pro.ip-api.com (a hung upstream pins the worker)
# and grows a module-global dict keyed by unauthenticated request IP without
# bound. hooks.py already removed its jinja reachability; the whitelist was the
# last live entry point and nothing in this app calls the function. Body kept
# for upstream-merge parity only — hrms/sync/client.py is this shape done right.
def get_country(fields: list | None = None) -> dict:
	global country_info
	ip = frappe.local.request_ip

	if ip not in country_info:
		fields = ["countryCode", "country", "regionName", "city"]
		res = requests.get(
			"https://pro.ip-api.com/json/{ip}?key={key}&fields={fields}".format(
				ip=ip, key=frappe.conf.get("ip-api-key"), fields=",".join(fields)
			)
		)

		try:
			country_info[ip] = res.json()

		except Exception:
			country_info[ip] = {}

	return country_info[ip]


def get_date_range(start_date: str, end_date: str) -> list[str]:
	"""returns list of dates between start and end dates"""
	no_of_days = date_diff(end_date, start_date) + 1
	return [add_days(start_date, i) for i in range(no_of_days)]


def generate_date_range(start_date: str, end_date: str, reverse: bool = False) -> Generator[str, None, None]:
	no_of_days = date_diff(end_date, start_date) + 1

	date_field = end_date if reverse else start_date
	direction = -1 if reverse else 1

	for n in range(no_of_days):
		yield add_days(date_field, direction * n)


def get_employee_email(employee_id: str) -> str | None:
	employee_emails = frappe.db.get_value(
		"Employee",
		employee_id,
		["prefered_email", "user_id", "company_email", "personal_email"],
		as_dict=True,
	)

	return (
		employee_emails.prefered_email
		or employee_emails.user_id
		or employee_emails.company_email
		or employee_emails.personal_email
	)
