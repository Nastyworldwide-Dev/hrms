__version__ = "15.106.2"


def refetch_resource(cache_key: str | list, user=None):
	# Deferred so importing `hrms` (or `hrms.utils.*` pure helpers) doesn't
	# require Frappe to be installed — needed to run unit tests outside of
	# a Frappe bench.
	import frappe

	frappe.publish_realtime(
		"hrms:refetch_resource",
		{"cache_key": cache_key},
		user=user or frappe.session.user,
		after_commit=True,
	)
