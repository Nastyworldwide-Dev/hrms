# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, cint, getdate, nowdate, strip_html

logger = logging.getLogger(__name__)

#: The doctype each audience names, used to CHECK that the value HR typed is a
#: real record. Not a Dynamic Link: Frappe resolves a Dynamic Link's target
#: during _validate_links(), which runs before every controller hook, so a
#: target derived from `audience` can never be populated in time. Verified on
#: the bench rather than reasoned about — the first two attempts (validate,
#: then before_validate) both threw "Audience DocType must be set first".
AUDIENCE_DOCTYPE = {
	"Company": "Company",
	"Department": "Department",
	"Branch": "Branch",
}

#: Two weeks. An announcement with no end date is a noticeboard that rots:
#: somebody has to remember to take it down, and nobody ever does. HR can
#: change it, but they never have to think about it.
DEFAULT_RUN_DAYS = 14

#: The summary is the push body too, and a phone shows about two lines (alpha.7 §10.1).
SUMMARY_MAX = 140


def summary_from(body) -> str:
	"""The first sentence-sized piece of the body, as plain text."""
	text = " ".join(strip_html(body or "").split())
	if len(text) <= SUMMARY_MAX:
		return text
	cut = text[: SUMMARY_MAX - 1].rsplit(" ", 1)[0]
	return f"{cut}…"


class HRAnnouncement(Document):
	def validate(self):
		self.set_defaults()
		self.resolve_audience()
		self.validate_dates()
		self.validate_event_date()
		self.enforce_single_pin()
		self.clean_summary()
		self.bump_version()

	def clean_summary(self):
		"""Plain words, short enough for a notification (alpha.7 §10.1). A
		notification shows no formatting, so none is kept."""
		self.summary = " ".join(strip_html(self.summary or "").split())
		if len(self.summary) > SUMMARY_MAX:
			frappe.throw(
				_("Keep the summary to {0} characters; it is {1}.").format(SUMMARY_MAX, len(self.summary))
			)
		if not self.summary:
			# Notices published before the field existed (and a hurried HR
			# save) get the opening words of the body; HR can rewrite it.
			self.summary = summary_from(self.body)

	def bump_version(self):
		"""A must-read notice whose words change is a new notice to confirm
		(alpha.7 4.3), unless HR marks the save a minor fix. The tick applies
		to one save only."""
		self.version = cint(self.version) or 1
		before = self.get_doc_before_save()
		changed = before and (before.title != self.title or (before.body or "") != (self.body or ""))
		if changed and before.published and self.acknowledge_required and not cint(self.minor_fix):
			self.version += 1
			logger.info("[announcement] %s words changed -> version %s", self.name, self.version)
		self.minor_fix = 0

	def set_defaults(self):
		"""HR types a title and a body; everything else has a right answer."""
		if not self.publish_from:
			self.publish_from = nowdate()
		if not self.publish_until:
			self.publish_until = add_days(self.publish_from, DEFAULT_RUN_DAYS)

	def resolve_audience(self):
		"""Everyone means everyone — the link is cleared rather than left
		holding whatever was picked before the audience changed, which would
		silently narrow a company-wide notice to one department."""
		if self.audience == "Everyone":
			self.audience_value = None
			return
		doctype = AUDIENCE_DOCTYPE.get(self.audience)
		if not doctype:
			frappe.throw(_("{0} is not an audience this app knows.").format(self.audience))
		if not self.audience_value:
			frappe.throw(_("Choose which {0} this is for.").format(self.audience.lower()))
		# The value is a typed name rather than a validated Link, so the check
		# is ours. Without it a typo publishes an announcement addressed to a
		# department that does not exist — which shows it to nobody, silently,
		# and HR has no way to tell that from "nobody has read it yet".
		if not frappe.db.exists(doctype, self.audience_value):
			frappe.throw(_("There is no {0} called {1}.").format(self.audience.lower(), self.audience_value))

	def validate_dates(self):
		if getdate(self.publish_until) < getdate(self.publish_from):
			frappe.throw(_("An announcement cannot stop showing before it starts."))

	def validate_event_date(self):
		"""An Event is a thing that happens on a day, and the calendar puts its dot on
		that day (owner, 27 Oct 2026). Any other category has no such day: one left
		behind by an edit from Event to Notice is cleared, not kept."""
		if self.category == "Event":
			if not self.event_date:
				frappe.throw(_("Choose the day this event happens."))
			return
		self.event_date = None

	def enforce_single_pin(self):
		"""One pin. Two pinned announcements are two things claiming to be the
		most important, which is the same as none — and the PWA gives the pin a
		fixed slot, so a second would displace the first with no way to tell
		which won."""
		if not self.pinned:
			return
		others = frappe.get_all(
			"HR Announcement",
			filters={"pinned": 1, "name": ("!=", self.name or "")},
			pluck="name",
		)
		if others:
			logger.info("[announcement] unpinning %s for %s", others, self.name)
			for name in others:
				# db_set, not a save: unpinning is a consequence of THIS edit and
				# must not re-run another document's validate — which would, among
				# other things, re-enforce this same rule and recurse.
				frappe.db.set_value("HR Announcement", name, "pinned", 0, update_modified=False)

	def on_update(self):
		"""Notify once, when it is first published (alpha.7 §10.1). An edit to
		a published notice does not buzz everybody's phone again.

		Only a notice live TODAY: one published for a later day was pushed at
		once, and the tap opened a board that did not show it yet (alpha.57).
		push_notices_going_live_today sends that one on its day."""
		before = self.get_doc_before_save()
		just_published = self.published and not (before and before.published)
		if not (just_published and cint(self.notify_on_publish)):
			return
		if getdate(self.publish_from) > getdate(nowdate()):
			logger.info("[announcement] %s published for %s; push waits", self.name, self.publish_from)
			return
		_queue_publish_push(self.name)

	def on_trash(self):
		"""The read rows are about a thing that no longer exists. Left behind
		they become an unreadable audit trail — a name, a date and a dangling
		link."""
		deleted = frappe.db.delete("HR Announcement Read", {"announcement": self.name})
		logger.info("[announcement] %s deleted, read rows removed: %s", self.name, deleted)


#: The mark a sent publish push leaves on the notice. A job id only dedupes while the job is
#: queued, so it cannot say "pushed once ever" (review of 22e6b92ac); a Comment needs no migrate.
PUSH_SENT = "Push sent"
#: How far back the daily job looks: a skipped scheduler day or a date edited to today still
#: pushes, an old notice never does.
CATCH_UP_DAYS = 2


def _queue_publish_push(name: str) -> None:
	"""Queue the publish push; send_publish_push checks the PUSH_SENT mark."""
	frappe.enqueue(
		"hrms.hr.doctype.hr_announcement.hr_announcement.send_publish_push",
		name=name,
		enqueue_after_commit=True,
		job_id=f"announcement_publish_push::{name}",
		deduplicate=True,
	)
	logger.info("[announcement] %s published; push queued", name)


def push_notices_going_live_today() -> None:
	"""Daily: push each published notice that went live in the last CATCH_UP_DAYS (alpha.57).
	Already-pushed ones are skipped by send_publish_push."""
	today = nowdate()
	names = frappe.get_all(
		"HR Announcement",
		filters={
			"published": 1,
			"notify_on_publish": 1,
			"publish_from": ("between", [str(getdate(add_days(today, -CATCH_UP_DAYS))), today]),
		},
		pluck="name",
	)
	for name in names:
		try:
			_queue_publish_push(name)
		except Exception:
			# one notice must not cost the others their push
			frappe.log_error(f"Announcement push not queued: {name}")
	logger.info("[announcement] %d notice(s) live in the catch-up window", len(names))


def send_publish_push(name: str) -> None:
	"""Background job: one push per person in the notice's audience, title and
	Summary, opening the notice in the app. Re-reads the committed row; a notice
	unpublished or deleted before the worker ran sends nothing."""
	if not frappe.db.exists("HR Announcement", name):
		return
	doc = frappe.get_doc("HR Announcement", name)
	if not doc.published:
		logger.info("[announcement] %s no longer published; no push", name)
		return
	if frappe.db.exists(
		"Comment", {"reference_doctype": "HR Announcement", "reference_name": name, "content": PUSH_SENT}
	):
		logger.info("[announcement] %s already pushed; not again", name)
		return
	from hrms.api.announcements import _audience_employees, _push_to_users

	users = frappe.get_all(
		"Employee",
		filters={"name": ("in", _audience_employees(doc) or [""]), "user_id": ("is", "set")},
		pluck="user_id",
	)
	# marked only when it reached someone: relay off or every send failed keeps it pushable
	# (the helper swallows per-user errors and returns a count; review of e413eaa50)
	if _push_to_users(doc, users):
		doc.add_comment("Info", PUSH_SENT)
