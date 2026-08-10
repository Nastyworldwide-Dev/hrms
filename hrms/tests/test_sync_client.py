"""Guards the safety property of `hrms.sync.client`: it can only ever read.

The remote instance in the shadow-sync design is nasty-live — live production
HR for ten companies. A single stray write from this side would corrupt data
nobody can reconstruct, so "read-only" is tested structurally (what methods can
possibly exist, what verb can possibly reach the wire) and not just behaviourally.

Bench-free by construction, like `test_company_settings.py`: `frappe` is not
importable outside a bench and importing `hrms.sync.client` normally drags in
the whole `hrms` package, so the module under test is loaded straight from its
file with stub `frappe` / `requests` in `sys.modules`. Run it as a FILE:

    python3 hrms/tests/test_sync_client.py

It also runs under `bench run-tests`, where the real frappe is already imported —
the tests patch only the attributes they need and restore them afterwards.
"""

import importlib.util
import pathlib
import re
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "sync" / "client.py"

API_KEY = "ak_live_key"
API_SECRET = "sk_live_super_secret_value"


class _FakeDB:
	"""Stands in for frappe.db — answers HRMS ERP Instance lookups from a canned table."""

	def __init__(self, instances=None):
		self.instances = instances or {}

	def get_value(self, doctype, filters, fieldname, **kwargs):
		if doctype != "HRMS ERP Instance":
			return None
		return self.instances.get(filters.get("instance_name"))


class _FakeResponse:
	def __init__(self, status_code=200, payload=None, bad_json=False):
		self.status_code = status_code
		self._payload = payload if payload is not None else {}
		self._bad_json = bad_json

	def json(self):
		if self._bad_json:
			raise ValueError("Expecting value: line 1 column 1")
		return self._payload


class _FakeRequests:
	"""Records every GET; blows up loudly if anything tries a write verb."""

	def __init__(self, responses=None):
		self.calls = []
		self.responses = list(responses or [])
		self.exceptions = types.SimpleNamespace(
			ConnectionError=_FakeConnectionError,
			Timeout=_FakeTimeout,
		)

	def get(self, url, params=None, headers=None, timeout=None):
		self.calls.append({"url": url, "params": params or {}, "headers": headers or {}, "timeout": timeout})
		if not self.responses:
			return _FakeResponse(200, {"data": []})
		nxt = self.responses.pop(0)
		if isinstance(nxt, Exception):
			raise nxt
		return nxt

	def _forbidden(self, *args, **kwargs):
		raise AssertionError("the sync client issued a write request")

	post = put = patch = delete = request = _forbidden


class _FakeConnectionError(Exception):
	pass


class _FakeTimeout(Exception):
	pass


def _load_module():
	"""Import sync/client.py with stub `frappe` / `requests`, no bench required."""
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe.db = None
		frappe.conf = {}
		sys.modules["frappe"] = frappe

	if "requests" not in sys.modules:
		requests = types.ModuleType("requests")
		requests.exceptions = types.SimpleNamespace(
			ConnectionError=_FakeConnectionError, Timeout=_FakeTimeout
		)
		sys.modules["requests"] = requests

	spec = importlib.util.spec_from_file_location("_hrms_sync_client_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


sc = _load_module()

ENABLED_NASTY = {"url": "https://nasty-live.example.com/", "enabled": 1}


class _ClientTestCase(unittest.TestCase):
	"""Swaps frappe.db / frappe.conf / client.requests for the duration of a test."""

	def setUp(self):
		import frappe

		self.frappe = frappe
		self._saved = (getattr(frappe, "db", None), getattr(frappe, "conf", None), sc.requests, sc._sleep)
		frappe.db = _FakeDB({"nasty-live": dict(ENABLED_NASTY)})
		frappe.conf = {
			sc.CREDENTIALS_CONFIG_KEY: {"nasty-live": {"api_key": API_KEY, "api_secret": API_SECRET}}
		}
		self.requests = _FakeRequests()
		sc.requests = self.requests
		self.slept = []
		sc._sleep = self.slept.append

	def tearDown(self):
		self.frappe.db, self.frappe.conf, sc.requests, sc._sleep = self._saved

	def client(self, instance_name="nasty-live"):
		return sc.RemoteInstanceClient(instance_name)

	def queue(self, *responses):
		self.requests.responses = list(responses)


class TestReadOnlyByConstruction(_ClientTestCase):
	def test_only_two_public_methods_exist(self):
		"""Adding any third public method is a deliberate, visible change."""
		public = {name for name in dir(sc.RemoteInstanceClient) if not name.startswith("_")}
		self.assertEqual(public, {"get_list", "count"})

	def test_module_never_names_a_write_verb_on_requests(self):
		source = MODULE_PATH.read_text(encoding="utf-8")
		code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
		offenders = re.findall(r"requests\.(post|put|patch|delete|request)\s*\(", code)
		self.assertEqual(offenders, [], f"sync client can issue write verbs: {offenders}")
		self.assertEqual(len(re.findall(r"requests\.get\s*\(", code)), 1)

	def test_injected_non_get_is_refused_before_any_request(self):
		client = self.client()
		for verb in ("POST", "PUT", "PATCH", "DELETE", "get"):
			with self.assertRaises(sc.RemoteInstanceError) as ctx:
				client._request("/api/resource/Employee", {}, method=verb)
			self.assertIn("read-only", str(ctx.exception))
		self.assertEqual(self.requests.calls, [], "a refused method still hit the network")

	def test_reads_use_get_only(self):
		self.queue(_FakeResponse(200, {"data": [{"name": "HR-EMP-001"}]}))
		self.client().get_list("Employee")
		self.assertEqual(len(self.requests.calls), 1)


class TestCredentials(_ClientTestCase):
	def test_missing_config_key_names_it(self):
		self.frappe.conf = {}
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client()
		message = str(ctx.exception)
		self.assertIn(sc.CREDENTIALS_CONFIG_KEY, message)
		self.assertIn("nasty-live", message)

	def test_missing_entry_for_instance_names_it(self):
		self.frappe.conf = {
			sc.CREDENTIALS_CONFIG_KEY: {"some-other-site": {"api_key": "x", "api_secret": "y"}}
		}
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client()
		self.assertIn("nasty-live", str(ctx.exception))

	def test_partial_credentials_name_the_missing_field(self):
		self.frappe.conf = {sc.CREDENTIALS_CONFIG_KEY: {"nasty-live": {"api_key": API_KEY}}}
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client()
		self.assertIn("api_secret", str(ctx.exception))

	def test_credentials_are_sent_as_a_token_header(self):
		self.queue(_FakeResponse(200, {"data": []}))
		self.client().get_list("Employee")
		self.assertEqual(self.requests.calls[0]["headers"]["Authorization"], f"token {API_KEY}:{API_SECRET}")


class TestSecretNeverLeaks(_ClientTestCase):
	def test_repr_redacts_key_and_secret(self):
		text = repr(self.client())
		self.assertNotIn(API_SECRET, text)
		self.assertNotIn(API_KEY, text)
		self.assertIn(sc.REDACTED, text)
		self.assertIn("nasty-live", text)

	def test_secret_absent_from_4xx_error(self):
		self.queue(_FakeResponse(403, {}))
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client().get_list("Employee")
		self.assertNotIn(API_SECRET, str(ctx.exception))
		self.assertNotIn(API_KEY, str(ctx.exception))

	def test_secret_absent_from_exhausted_retry_error(self):
		self.queue(*[_FakeResponse(502, {}) for _ in range(sc.MAX_ATTEMPTS)])
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client().count("Attendance")
		self.assertNotIn(API_SECRET, str(ctx.exception))

	def test_secret_absent_from_refused_method_error(self):
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client()._request("/api/resource/Employee", {}, method="DELETE")
		self.assertNotIn(API_SECRET, str(ctx.exception))


class TestInstanceResolution(_ClientTestCase):
	def test_unknown_instance_is_refused(self):
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client("does-not-exist")
		self.assertIn("unknown", str(ctx.exception))

	def test_disabled_instance_is_refused(self):
		self.frappe.db = _FakeDB({"nasty-live": {"url": "https://nasty-live.example.com", "enabled": 0}})
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client()
		self.assertIn("disabled", str(ctx.exception))

	def test_instance_without_url_is_refused(self):
		self.frappe.db = _FakeDB({"nasty-live": {"url": "  ", "enabled": 1}})
		with self.assertRaises(sc.RemoteInstanceError):
			self.client()

	def test_blank_instance_name_is_a_programming_error(self):
		with self.assertRaises(ValueError):
			sc.RemoteInstanceClient("")

	def test_trailing_slash_does_not_double_up(self):
		self.queue(_FakeResponse(200, {"data": []}))
		self.client().get_list("Employee")
		self.assertEqual(
			self.requests.calls[0]["url"], "https://nasty-live.example.com/api/resource/Employee"
		)


class TestRetryPolicy(_ClientTestCase):
	def test_retries_on_5xx_then_succeeds(self):
		self.queue(
			_FakeResponse(500, {}),
			_FakeResponse(200, {"data": [{"name": "HR-EMP-001"}]}),
		)
		rows = self.client().get_list("Employee")
		self.assertEqual(rows, [{"name": "HR-EMP-001"}])
		self.assertEqual(len(self.requests.calls), 2)
		self.assertEqual(len(self.slept), 1)

	def test_5xx_retries_are_capped(self):
		self.queue(*[_FakeResponse(503, {}) for _ in range(sc.MAX_ATTEMPTS + 2)])
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client().get_list("Employee")
		self.assertEqual(len(self.requests.calls), sc.MAX_ATTEMPTS)
		self.assertEqual(ctx.exception.status_code, 503)
		self.assertEqual(ctx.exception.endpoint, "/api/resource/Employee")

	def test_no_retry_on_404(self):
		self.queue(_FakeResponse(404, {}), _FakeResponse(200, {"data": [{"name": "x"}]}))
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client().get_list("Nonexistent DocType")
		self.assertEqual(len(self.requests.calls), 1, "a 404 was retried")
		self.assertEqual(ctx.exception.status_code, 404)
		self.assertEqual(self.slept, [])

	def test_no_retry_on_403(self):
		self.queue(_FakeResponse(403, {}), _FakeResponse(200, {"data": []}))
		with self.assertRaises(sc.RemoteInstanceError):
			self.client().count("Employee")
		self.assertEqual(len(self.requests.calls), 1)

	def test_retries_on_connection_error(self):
		self.queue(
			_FakeConnectionError("connection refused"),
			_FakeResponse(200, {"message": 42}),
		)
		self.assertEqual(self.client().count("Attendance"), 42)
		self.assertEqual(len(self.requests.calls), 2)

	def test_non_json_body_is_a_typed_error(self):
		self.queue(_FakeResponse(200, bad_json=True))
		with self.assertRaises(sc.RemoteInstanceError) as ctx:
			self.client().get_list("Employee")
		self.assertIn("non-JSON", str(ctx.exception))


class TestTimeout(_ClientTestCase):
	def test_timeout_is_passed_on_every_call(self):
		self.queue(
			_FakeResponse(500, {}),
			_FakeResponse(200, {"data": [{"name": "a"}] * sc.PAGE_SIZE}),
			_FakeResponse(200, {"data": [{"name": "b"}]}),
		)
		self.client().get_list("Attendance")
		self.assertEqual(len(self.requests.calls), 3)
		for call in self.requests.calls:
			self.assertEqual(call["timeout"], sc.TIMEOUT)

	def test_timeout_is_a_connect_read_pair(self):
		self.assertIsInstance(sc.TIMEOUT, tuple)
		self.assertEqual(len(sc.TIMEOUT), 2)
		self.assertTrue(all(t > 0 for t in sc.TIMEOUT))


class TestPagination(_ClientTestCase):
	def _page(self, prefix, size):
		return [{"name": f"{prefix}-{i}"} for i in range(size)]

	def test_pages_are_assembled_in_order(self):
		first = self._page("p1", sc.PAGE_SIZE)
		second = self._page("p2", sc.PAGE_SIZE)
		third = self._page("p3", 7)
		self.queue(
			_FakeResponse(200, {"data": first}),
			_FakeResponse(200, {"data": second}),
			_FakeResponse(200, {"data": third}),
		)
		rows = self.client().get_list("Attendance")
		self.assertEqual(rows, first + second + third)
		self.assertEqual(len(self.requests.calls), 3)
		self.assertEqual(
			[call["params"]["limit_start"] for call in self.requests.calls],
			[0, sc.PAGE_SIZE, 2 * sc.PAGE_SIZE],
		)

	def test_short_first_page_stops_paging(self):
		self.queue(_FakeResponse(200, {"data": self._page("p1", 3)}))
		self.assertEqual(len(self.client().get_list("Employee")), 3)
		self.assertEqual(len(self.requests.calls), 1)

	def test_limit_caps_total_rows_across_pages(self):
		self.queue(
			_FakeResponse(200, {"data": self._page("p1", sc.PAGE_SIZE)}),
			_FakeResponse(200, {"data": self._page("p2", 10)}),
		)
		rows = self.client().get_list("Attendance", limit=sc.PAGE_SIZE + 10)
		self.assertEqual(len(rows), sc.PAGE_SIZE + 10)
		self.assertEqual(self.requests.calls[1]["params"]["limit_page_length"], 10)

	def test_limit_smaller_than_a_page_asks_for_exactly_that_many(self):
		self.queue(_FakeResponse(200, {"data": self._page("p1", 5)}))
		self.client().get_list("Employee", limit=5)
		self.assertEqual(self.requests.calls[0]["params"]["limit_page_length"], 5)
		self.assertEqual(len(self.requests.calls), 1)

	def test_zero_limit_makes_no_request(self):
		self.assertEqual(self.client().get_list("Employee", limit=0), [])
		self.assertEqual(self.requests.calls, [])

	def test_start_offset_is_honoured(self):
		self.queue(_FakeResponse(200, {"data": self._page("p1", 2)}))
		self.client().get_list("Employee", start=100)
		self.assertEqual(self.requests.calls[0]["params"]["limit_start"], 100)

	def test_empty_result_returns_empty_list(self):
		self.queue(_FakeResponse(200, {"data": []}))
		self.assertEqual(self.client().get_list("Employee"), [])


class TestQueryEncoding(_ClientTestCase):
	def test_filters_fields_and_order_by_are_encoded(self):
		self.queue(_FakeResponse(200, {"data": []}))
		self.client().get_list(
			"Attendance",
			filters={"docstatus": 1},
			fields=["name", "employee"],
			order_by="modified desc",
		)
		params = self.requests.calls[0]["params"]
		self.assertEqual(params["filters"], '{"docstatus": 1}')
		self.assertEqual(params["fields"], '["name", "employee"]')
		self.assertEqual(params["order_by"], "modified desc")

	def test_doctype_with_spaces_is_url_quoted(self):
		self.queue(_FakeResponse(200, {"data": []}))
		self.client().get_list("Employee Checkin")
		self.assertTrue(self.requests.calls[0]["url"].endswith("/api/resource/Employee%20Checkin"))

	def test_count_uses_the_get_count_endpoint(self):
		self.queue(_FakeResponse(200, {"message": 4636}))
		self.assertEqual(self.client().count("Attendance", filters={"docstatus": 1}), 4636)
		call = self.requests.calls[0]
		self.assertTrue(call["url"].endswith("/api/method/frappe.client.get_count"))
		self.assertEqual(call["params"]["doctype"], "Attendance")

	def test_count_of_nothing_is_zero(self):
		self.queue(_FakeResponse(200, {"message": None}))
		self.assertEqual(self.client().count("Attendance"), 0)

	def test_blank_doctype_is_a_programming_error(self):
		client = self.client()
		with self.assertRaises(ValueError):
			client.get_list("")
		with self.assertRaises(ValueError):
			client.count("")


if __name__ == "__main__":
	unittest.main()
