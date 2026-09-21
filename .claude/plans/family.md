# Family — fix(checkin): a retry after a lost response is the same tap (21 Sep 2026)
CLASS: no idempotency key on a tap — the server cannot tell "the same tap again" from "a new tap", so the burst window (45 s) and the IN→OUT coercion turned a retry into a check-out
Changed symbols: remote_checkin.punch (client_tap_id parameter, _stored_tap pre-check, UniqueValidationError replay path, single return via _punch_result), _punch_result, _reason_on_record, _stored_tap (new); Employee Checkin JSON field client_tap_id (unique); CheckInPanel.vue pending id per employee in localStorage.
frontend/src/components/CheckInPanel.vue same-root — the one caller of punch from the PWA; sends the id, keeps it until 2xx, arms the guard + reloads on error
hrms/api/remote_checkin.py:submit_late_checkout not-affected — a typed late OUT, not a tap; no id, inserts as before
hrms/hr/doctype/employee_checkin/employee_checkin_override.py:fetch_shift / _restamp_later_session_punches not-affected — run inside insert as before; the replay path never reaches insert
hrms/overrides/remote_checkin_request_hooks.py not-affected — after_insert hooks do not fire on the refused duplicate insert (verified: no before_insert hook on Employee Checkin; validate writes nothing except the strict-throw reject log which never reaches insert)
hrms/sync/runner.py, checkin_import.py, checkin_recovery.py, lone_in_closer.py not-affected — insert punches without an id (NULL is allowed many times under the unique index)
Desk Employee Checkin form not-affected — field hidden + read_only; Desk never sends an id
Machine hits for the symbol `punch` are log-string matches (see previous ledger); PIPELINE_SKIP_FAMILY used on that basis if the gate lists them again.
