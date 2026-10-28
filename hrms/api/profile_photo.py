"""Profile photo set/remove endpoints.

Everyone using Nadi sets their own photo, stored on S3, max 5 MB, private
(owner 28 Oct 2026).

	hrms.api.profile_photo.set_photo(image: str) -> dict
	hrms.api.profile_photo.remove_photo() -> dict
	hrms.api.profile_photo.photo_url(employee: str) -> str
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import re
import time as time_module
from urllib.parse import quote

import frappe
from frappe import _

from hrms.utils.identity import require_employee

logger = logging.getLogger(__name__)

#: Allowed MIME types for profile photos
PHOTO_MIMETYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

#: Max photo size in bytes (5 MB)
PHOTO_MAX_BYTES = 5 * 1024 * 1024


def _has_image_signature(content: bytes) -> bool:
	"""True when the bytes start like a JPEG, PNG or WebP (the header is not trusted)."""
	return (
		content.startswith(b"\xff\xd8\xff")
		or content.startswith(b"\x89PNG")
		or (content[:4] == b"RIFF" and content[8:12] == b"WEBP")
	)


@frappe.whitelist(methods=["POST"])
def set_photo(image: str) -> dict:
	"""Set the caller's profile photo and return the photo URL.

	The photo is stored as a private File attached to the Employee record,
	and the Employee.image field points to it. The S3 app's after_insert
	hook moves it to S3.

	Args:
		image: data URL with base64-encoded image data (e.g. "data:image/jpeg;base64,...")

	Returns:
		dict with "image" key containing the photo URL

	Raises:
		frappe.ValidationError: if the image is invalid, unsupported, or too large
	"""
	employee = require_employee()

	# Parse the data URL
	header, _sep, payload = (image or "").partition(",")
	mimetype = header[5:].split(";")[0].strip().lower() if header.startswith("data:") else ""
	extension = PHOTO_MIMETYPES.get(mimetype)
	if not extension or not payload:
		logger.warning("[profile_photo] photo refused for %s: mimetype=%r", employee, mimetype)
		frappe.throw(_("A profile photo must be a JPEG, PNG or WebP image."))

	# Decode base64
	try:
		content = base64.b64decode(payload, validate=True)
	except (binascii.Error, ValueError):
		logger.warning("[profile_photo] photo refused for %s: undecodable", employee)
		frappe.throw(_("The photo could not be read. Try again."))

	# Check size
	if len(content) > PHOTO_MAX_BYTES:
		logger.warning(
			"[profile_photo] photo refused for %s: %d bytes over the %d limit",
			employee,
			len(content),
			PHOTO_MAX_BYTES,
		)
		frappe.throw(_("This photo is over 5 MB. Pick a smaller one."))

	# The data-url header is client-supplied: the real bytes must be an image too
	if not _has_image_signature(content):
		logger.warning("[profile_photo] photo refused for %s: bytes are not an image", employee)
		frappe.throw(_("A profile photo must be a JPEG, PNG or WebP image."))

	# Create File document (as in upload_selfie)
	slug = re.sub(r"[^A-Za-z0-9_-]", "", str(employee))[:40] or "employee"
	stored = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"photo-{slug}-{int(time_module.time() * 1000)}.{extension}",
			"content": content,
			"is_private": 1,
			"attached_to_doctype": "Employee",
			"attached_to_name": employee,
			"attached_to_field": "image",
		}
	).insert(ignore_permissions=True)

	# Read back the file_url from the stored File (S3 hook may have modified it)
	file_url = frappe.db.get_value("File", stored.name, "file_url")

	# Set Employee.image and User.user_image
	frappe.db.set_value("Employee", employee, "image", file_url, update_modified=False)
	user_id = frappe.db.get_value("Employee", employee, "user_id")
	if user_id:
		frappe.db.set_value("User", user_id, "user_image", file_url, update_modified=False)

	# Delete old photos (all Files attached to this employee's image field except the new one)
	old_files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Employee",
			"attached_to_name": employee,
			"attached_to_field": "image",
			"name": ("!=", stored.name),
		},
		pluck="name",
	)
	for file_name in old_files:
		frappe.delete_doc(
			"File", file_name, ignore_permissions=True
		)  # file_name is a string when using pluck

	logger.info("[profile_photo] photo stored for %s: %s", employee, file_url)
	return {"image": photo_url(employee)}


@frappe.whitelist(methods=["POST"])
def remove_photo() -> dict:
	"""Remove the caller's profile photo.

	Deletes all Files attached to the Employee's image field and clears
	the Employee.image and User.user_image fields.

	Returns:
		dict with "image" key set to empty string
	"""
	employee = require_employee()

	# Delete all Files attached to this employee's image field
	files = frappe.get_all(
		"File",
		filters={
			"attached_to_doctype": "Employee",
			"attached_to_name": employee,
			"attached_to_field": "image",
		},
		pluck="name",
	)
	for file_name in files:
		frappe.delete_doc("File", file_name, ignore_permissions=True)

	# Clear Employee.image and User.user_image
	frappe.db.set_value("Employee", employee, "image", "", update_modified=False)
	user_id = frappe.db.get_value("Employee", employee, "user_id")
	if user_id:
		frappe.db.set_value("User", user_id, "user_image", "", update_modified=False)

	logger.info("[profile_photo] photo removed for %s", employee)
	return {"image": ""}


def photo_url(employee: str) -> str:
	"""Get the photo URL for an employee, with cache-busting query string.

	Args:
		employee: employee ID

	Returns:
		URL to fetch the photo via the org_chart endpoint, or empty string if no photo set
	"""
	image_value = frappe.db.get_value("Employee", employee, "image") or ""
	if not image_value:
		return ""

	# Use last 8 chars of SHA1 hash of the image value for cache-busting
	image_hash = hashlib.sha1(image_value.encode()).hexdigest()
	cache_buster = image_hash[-8:]

	return f"/api/method/hrms.api.org_chart.photo?employee={quote(employee)}&v={cache_buster}"
