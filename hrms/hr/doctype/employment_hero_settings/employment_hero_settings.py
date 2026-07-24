# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode

import requests

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_to_date, get_datetime, now_datetime

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


def _generate_pkce_pair():
	"""RFC 7636 PKCE: a random code_verifier and its S256 code_challenge."""
	verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).decode("ascii").rstrip("=")
	digest = hashlib.sha256(verifier.encode("ascii")).digest()
	challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
	return verifier, challenge


class EmploymentHeroSettings(Document):
	def get_authorize_url(self):
		"""Build the OAuth2 authorization URL with a fresh PKCE challenge and stash
		the verifier (encrypted) for the callback to complete the exchange."""
		logger.info("[employment_hero] building authorize URL")
		if not self.client_id or not self.redirect_uri:
			frappe.throw(_("Set Client ID and Redirect URI before connecting."))
		verifier, challenge = _generate_pkce_pair()
		self.code_verifier = verifier
		self.save(ignore_permissions=True)
		params = {
			"response_type": "code",
			"client_id": self.client_id,
			"redirect_uri": self.redirect_uri,
			"code_challenge": challenge,
			"code_challenge_method": "S256",
		}
		return f"{self.authorize_url}?{urlencode(params)}"

	def exchange_code(self, code):
		"""Exchange an authorization code + the stored PKCE verifier for tokens."""
		logger.info("[employment_hero] exchanging authorization code for tokens")
		self._request_tokens(
			{
				"grant_type": "authorization_code",
				"code": code,
				"redirect_uri": self.redirect_uri,
				"client_id": self.client_id,
				"client_secret": self.get_password("client_secret", raise_exception=False),
				"code_verifier": self.get_password("code_verifier", raise_exception=False),
			}
		)

	def refresh_access_token(self):
		"""Renew the access token from the stored refresh token."""
		logger.info("[employment_hero] refreshing access token")
		refresh = self.get_password("refresh_token", raise_exception=False)
		if not refresh:
			frappe.throw(_("No refresh token stored. Re-connect to Employment Hero."))
		self._request_tokens(
			{
				"grant_type": "refresh_token",
				"refresh_token": refresh,
				"client_id": self.client_id,
				"client_secret": self.get_password("client_secret", raise_exception=False),
			}
		)

	def _request_tokens(self, data):
		"""POST to the token endpoint and persist the returned tokens (encrypted)."""
		logger.info("[employment_hero] token request grant=%s", data.get("grant_type"))
		resp = requests.post(self.token_url, data=data, timeout=REQUEST_TIMEOUT)
		if not resp.ok:
			logger.error("[employment_hero] token request failed %s: %s", resp.status_code, resp.text[:300])
			frappe.throw(_("Employment Hero token request failed ({0}).").format(resp.status_code))
		payload = resp.json()
		self.access_token = payload.get("access_token")
		if payload.get("refresh_token"):
			self.refresh_token = payload.get("refresh_token")
		self.token_expiry = add_to_date(now_datetime(), seconds=int(payload.get("expires_in") or 900))
		self.code_verifier = None
		self.save(ignore_permissions=True)

	def get_valid_access_token(self):
		"""Return a non-expired access token, refreshing first if needed."""
		logger.info("[employment_hero] resolving valid access token")
		if not self.get_password("access_token", raise_exception=False):
			frappe.throw(_("Employment Hero is not connected yet. Authorize it first."))
		if not self.token_expiry or get_datetime(self.token_expiry) <= now_datetime():
			self.refresh_access_token()
		return self.get_password("access_token", raise_exception=False)


@frappe.whitelist()
def get_authorize_url():
	return frappe.get_single("Employment Hero Settings").get_authorize_url()


@frappe.whitelist()
def oauth_callback(code=None, **kwargs):
	"""OAuth redirect target — Employment Hero sends ?code=... here after the
	admin authorizes; exchange it and drop back to the settings form."""
	logger.info("[employment_hero] oauth callback received code=%s", bool(code))
	if not code:
		frappe.throw(_("Employment Hero did not return an authorization code."))
	frappe.get_single("Employment Hero Settings").exchange_code(code)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = "/app/employment-hero-settings"


@frappe.whitelist()
def test_connection():
	"""Ping the organisation endpoint with a valid token to confirm the link."""
	logger.info("[employment_hero] test connection")
	doc = frappe.get_single("Employment Hero Settings")
	token = doc.get_valid_access_token()
	url = f"{doc.api_base_url}/api/v1/organisations/{doc.organisation_id}"
	resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=REQUEST_TIMEOUT)
	if not resp.ok:
		frappe.throw(_("Employment Hero API returned {0}.").format(resp.status_code))
	name = (resp.json() or {}).get("data", {}).get("name")
	return {"ok": True, "organisation": name}
