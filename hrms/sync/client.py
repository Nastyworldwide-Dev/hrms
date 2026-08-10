"""Read-only HTTP client for a remote ERPNext instance.

Used by the one-way shadow sync (nasty-live -> verifica-live). The remote is
**live production for ten companies**, so the non-negotiable property of this
module is that it can never write to it:

* the class exposes exactly two public data methods, `get_list` and `count`;
* every request funnels through `_request`, which refuses any HTTP method other
  than GET before a socket is opened;
* the actual call is a hard-coded `requests.get` — there is no code path in this
  file that can emit POST/PUT/PATCH/DELETE, so adding one is a visible diff, not
  an accident.

Credentials live in site config (`hrms_sync_credentials`), never in a DocType,
and are redacted from `repr()` and from every error this module raises.
"""

import json
import logging
import time
from urllib.parse import quote

try:
	import requests
except ImportError:  # pragma: no cover — pure unit tests outside bench
	requests = None

import frappe

logger = logging.getLogger(__name__)

#: The only HTTP method this client may ever issue.
ALLOWED_HTTP_METHOD = "GET"

#: Site-config key holding `{instance_name: {"api_key": ..., "api_secret": ...}}`.
CREDENTIALS_CONFIG_KEY = "hrms_sync_credentials"

#: (connect, read) seconds. Always passed — a request with no timeout can hang a worker forever.
TIMEOUT = (10, 60)

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5
PAGE_SIZE = 500
#: Stops a remote that ignores `limit_start` from looping us forever.
MAX_PAGES = 2000

REDACTED = "***redacted***"


class RemoteInstanceError(Exception):
	"""A remote read failed. Carries status code and endpoint — never credentials."""

	def __init__(self, message: str, status_code: int | None = None, endpoint: str | None = None):
		self.status_code = status_code
		self.endpoint = endpoint
		detail = []
		if status_code is not None:
			detail.append(f"status={status_code}")
		if endpoint:
			detail.append(f"endpoint={endpoint}")
		super().__init__(f"{message} ({', '.join(detail)})" if detail else message)


def _retryable_exceptions() -> tuple:
	"""Connection-level failures worth retrying; empty when `requests` is absent."""
	exceptions = getattr(requests, "exceptions", None)
	if exceptions is None:
		return ()
	return tuple(
		exc
		for exc in (
			getattr(exceptions, "ConnectionError", None),
			getattr(exceptions, "Timeout", None),
		)
		if isinstance(exc, type)
	)


def _sleep(seconds: float) -> None:
	"""Indirection so tests can neutralise backoff without patching `time` globally."""
	time.sleep(seconds)


class RemoteInstanceClient:
	"""Reads documents from another ERPNext instance. Cannot write to it.

	client = RemoteInstanceClient("nasty-live")
	rows = client.get_list("Attendance", filters={"docstatus": 1}, limit=5000)
	"""

	def __init__(self, instance_name: str):
		if not instance_name:
			raise ValueError("instance_name is required")

		self.instance_name = instance_name
		self.url = self._resolve_url(instance_name)
		self._api_key, self._api_secret = self._load_credentials(instance_name)
		logger.info("[sync] client ready for instance %s at %s", instance_name, self.url)

	# -- construction helpers -------------------------------------------------

	@staticmethod
	def _resolve_url(instance_name: str) -> str:
		row = frappe.db.get_value(
			"HRMS ERP Instance",
			{"instance_name": instance_name},
			["url", "enabled"],
			as_dict=True,
		)
		if not row:
			logger.warning("[sync] unknown instance %s", instance_name)
			raise RemoteInstanceError(f"unknown HRMS ERP Instance {instance_name!r}")

		if not row.get("enabled"):
			logger.warning("[sync] instance %s is disabled", instance_name)
			raise RemoteInstanceError(f"HRMS ERP Instance {instance_name!r} is disabled")

		url = (row.get("url") or "").strip()
		if not url:
			raise RemoteInstanceError(f"HRMS ERP Instance {instance_name!r} has no URL configured")

		return url.rstrip("/")

	@staticmethod
	def _load_credentials(instance_name: str) -> tuple[str, str]:
		"""From site config only — deliberately not readable through the Desk."""
		credentials = frappe.conf.get(CREDENTIALS_CONFIG_KEY, {}) or {}
		entry = credentials.get(instance_name) or {}

		if not entry:
			raise RemoteInstanceError(
				f"site config key '{CREDENTIALS_CONFIG_KEY}' has no entry for instance "
				f"{instance_name!r}; add {{'api_key': ..., 'api_secret': ...}} to site_config.json"
			)

		missing = [key for key in ("api_key", "api_secret") if not entry.get(key)]
		if missing:
			raise RemoteInstanceError(
				f"site config '{CREDENTIALS_CONFIG_KEY}.{instance_name}' is missing {', '.join(missing)}"
			)

		return entry["api_key"], entry["api_secret"]

	def __repr__(self) -> str:
		# Never interpolate the key or secret here: reprs land in logs and tracebacks.
		return (
			f"<RemoteInstanceClient instance={self.instance_name!r} url={self.url!r} "
			f"api_key={REDACTED} api_secret={REDACTED}>"
		)

	# -- public read API ------------------------------------------------------

	def get_list(
		self,
		doctype: str,
		filters=None,
		fields: list | None = None,
		limit: int | None = None,
		start: int = 0,
		order_by: str | None = None,
	) -> list[dict]:
		"""Rows of `doctype` from the remote, paginated transparently.

		`limit` is a total row cap across pages (None = everything matching).
		"""
		if not doctype:
			raise ValueError("doctype is required")

		remaining = None if limit is None else max(int(limit), 0)
		if remaining == 0:
			return []

		endpoint = f"/api/resource/{quote(doctype)}"
		offset = int(start or 0)
		rows: list[dict] = []

		for page_number in range(1, MAX_PAGES + 1):
			page_size = PAGE_SIZE if remaining is None else min(PAGE_SIZE, remaining)
			params = {"limit_start": offset, "limit_page_length": page_size}
			if filters:
				params["filters"] = json.dumps(filters)
			if fields:
				params["fields"] = json.dumps(fields)
			if order_by:
				params["order_by"] = order_by

			page = self._get(endpoint, params).get("data") or []
			rows.extend(page)
			offset += len(page)
			if remaining is not None:
				remaining -= len(page)
				if remaining <= 0:
					break
			if len(page) < page_size:
				break
			if page_number == MAX_PAGES:
				logger.warning(
					"[sync] %s %s hit the %s-page cap at %s rows — remote may be ignoring limit_start",
					self.instance_name,
					doctype,
					MAX_PAGES,
					len(rows),
				)

		logger.info("[sync] %s %s -> %s rows", self.instance_name, endpoint, len(rows))
		return rows

	def count(self, doctype: str, filters=None) -> int:
		"""How many `doctype` rows match on the remote."""
		if not doctype:
			raise ValueError("doctype is required")

		params = {"doctype": doctype}
		if filters:
			params["filters"] = json.dumps(filters)

		endpoint = "/api/method/frappe.client.get_count"
		total = int(self._get(endpoint, params).get("message") or 0)
		logger.info("[sync] %s count %s -> %s", self.instance_name, doctype, total)
		return total

	# -- transport ------------------------------------------------------------

	def _auth_headers(self) -> dict:
		return {
			"Authorization": f"token {self._api_key}:{self._api_secret}",
			"Accept": "application/json",
		}

	def _get(self, endpoint: str, params: dict) -> dict:
		return self._request(endpoint, params, method=ALLOWED_HTTP_METHOD)

	def _request(self, endpoint: str, params: dict, method: str = ALLOWED_HTTP_METHOD) -> dict:
		"""The single exit to the network. GET only, by assertion and by call site."""
		if method != ALLOWED_HTTP_METHOD:
			logger.error("[sync] refused %s %s — this client is read-only", method, endpoint)
			raise RemoteInstanceError(
				f"refusing {method}: RemoteInstanceClient is read-only and may only issue "
				f"{ALLOWED_HTTP_METHOD}",
				endpoint=endpoint,
			)

		if requests is None:
			raise RemoteInstanceError("the `requests` library is unavailable", endpoint=endpoint)

		url = f"{self.url}{endpoint}"
		retryable = _retryable_exceptions()
		last_error: str | None = None
		last_status: int | None = None

		for attempt in range(1, MAX_ATTEMPTS + 1):
			try:
				# Hard-coded GET: no variable verb reaches `requests` from this module.
				response = requests.get(
					url,
					params=params,
					headers=self._auth_headers(),
					timeout=TIMEOUT,
				)
			except retryable as exc:  # connection refused / DNS / socket timeout
				last_error = f"connection error: {exc}"
				last_status = None
			else:
				status = int(getattr(response, "status_code", 0) or 0)
				if status >= 500:
					last_error = f"remote returned {status}"
					last_status = status
				elif status >= 400:
					# Client errors are deterministic — retrying only burns the remote.
					logger.warning("[sync] %s %s failed with %s", self.instance_name, endpoint, status)
					raise RemoteInstanceError(
						"remote rejected the read", status_code=status, endpoint=endpoint
					)
				else:
					try:
						payload = response.json()
					except Exception as exc:
						raise RemoteInstanceError(
							f"remote returned a non-JSON body: {exc}",
							status_code=status,
							endpoint=endpoint,
						)
					return payload if isinstance(payload, dict) else {"data": payload}

			logger.warning(
				"[sync] %s %s attempt %s/%s failed (%s)",
				self.instance_name,
				endpoint,
				attempt,
				MAX_ATTEMPTS,
				last_error,
			)
			if attempt < MAX_ATTEMPTS:
				_sleep(RETRY_BACKOFF_SECONDS * attempt)

		raise RemoteInstanceError(
			f"giving up after {MAX_ATTEMPTS} attempts ({last_error})",
			status_code=last_status,
			endpoint=endpoint,
		)
