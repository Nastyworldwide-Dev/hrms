"""Performance Review Type on Appraisal, and HR's starting list (owner, 13 Nov 2026).

The Appraisal field comes from the doctype JSON on migrate; this loads the new
list doctype and seeds the five types HR named. Idempotent: only missing types
are added, so one HR renamed or switched off is never put back.
"""

import frappe

from hrms.utils.performance_review_type import seed_review_types


def execute():
	frappe.reload_doc("hr", "doctype", "performance_review_type")
	frappe.reload_doc("hr", "doctype", "appraisal")
	seed_review_types()
