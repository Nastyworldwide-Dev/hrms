# HANDOFF
prompt:   real-world reliability + UX sweep (untested/unknown failure paths)
status:   partial
commit:   764515cf6 on nz-glass (16 fixes this session)
files:    CheckInPanel.vue RequestActionSheet.vue FormView.vue ListView.vue
          Profile.vue composables/realtime.js composables/useCurrencyConversion.js
          views/kpi/Dashboard.vue AttendanceCalendar.vue router+main (orphan route)
          hrms/api/__init__.py + ot_request.py (+ tests) — OT fractional pay
verify:   cd frontend && yarn build && node --test "src/**/*.test.js"  (48 pass)
          ruff check hrms/  (clean); OT python tests NOT run here (bench bootstrap
          broken — MagicMock/orjson), verified by logic+ruff, will run in CI
flags:    OT fractional-pay confirmed by product owner. DEFERRED: GDatePicker
          min/max (frappe-ui 0.1.105 has no support; server-guarded), FormField
          validation field-flag (error text shows; border/aria needs 6-control
          rework + preview). Pre-commit hook bundles co-modified files into one
          commit (2 fixes landed co-located but correct).
next:     remaining P2/minor: dirty-guard on back-nav, double-submit dialog
          disable, empty required child-table, OTP new-tab, push taps non-Chrome,
          timezone plugin (needs site-TZ decision). None are crashes/dead-ends.
