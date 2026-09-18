"""Make the check-in photos already stored PUBLIC private, and hang them on their punch.

Live, 18 Sep 2026: Remote Approvals showed a broken image where each face
should be. `upload_selfie` stored the File public, and with S3 configured the S3
hook rewrites a public file's url to the bucket object itself
(`{endpoint}/{bucket}/{key}`) — which is only readable with a public-read ACL
the bucket does not grant. The approver got a 403 and an empty frame.

New photos are private and attached to their punch. These are the ones already
taken. For each punch carrying a selfie whose File is still public:

  * the File becomes private and is attached to its Employee Checkin, so
    `File.is_downloadable` grants everyone who can read that punch — which is
    the set allowed to judge it, and no one else with the link;
  * if its url was a bucket url, it is rewritten to the `generate_file` api url,
    the shape the S3 hook itself uses for a private file. The object does not
    move; only the address changes.
  * the punch's own `selfie_image` is updated to match.

A photo whose url is already local (`/files/...`, no S3 on this site) or already
an api url is left exactly as it is, apart from going private and gaining its
parent.

Idempotent: a File that is already private and attached is skipped.
"""

import logging

import frappe

from hrms.api.remote_checkin import s3_key_from_public_url

logger = logging.getLogger(__name__)

PRIVATE_URL = "/api/method/frappe_s3_attachment.controller.generate_file?key={0}&file_name={1}"


def execute():
	punches = frappe.get_all(
		"Employee Checkin",
		filters={"selfie_image": ["is", "set"]},
		fields=["name", "selfie_image"],
		limit_page_length=0,
	)
	logger.info("[repair_public_selfies] %d punch(es) carry a photo", len(punches))
	repaired = 0
	for punch in punches:
		if _repair_one(punch):
			repaired += 1
	logger.info("[repair_public_selfies] %d photo(s) made private and attached", repaired)


def _repair_one(punch) -> bool:
	url = punch.get("selfie_image")
	stored = frappe.db.get_value(
		"File", {"file_url": url}, ["name", "file_name", "is_private", "attached_to_name"], as_dict=True
	)
	if not stored:
		logger.warning("[repair_public_selfies] punch %s names a photo with no File: %s", punch.name, url)
		return False
	if stored.is_private and stored.attached_to_name == punch.name:
		return False

	fields = {
		"is_private": 1,
		"attached_to_doctype": "Employee Checkin",
		"attached_to_name": punch.name,
	}
	key = s3_key_from_public_url(url)
	if key:
		# The object stays where it is; a private file is addressed through the
		# site instead of the bucket.
		fields["file_url"] = PRIVATE_URL.format(key, frappe.utils.quoted(stored.file_name or ""))
		frappe.db.set_value("Employee Checkin", punch.name, "selfie_image", fields["file_url"])
	frappe.db.set_value("File", stored.name, fields, update_modified=False)
	logger.info(
		"[repair_public_selfies] %s is private and attached to %s%s",
		stored.name,
		punch.name,
		" (readdressed)" if key else "",
	)
	return True
