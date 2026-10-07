# Ticket: roster.py hotspot (4 fixes/90d)
roster.py re-derives "may this caller touch this row" per endpoint (insert_shift `may`, break_shift own_line, swap/schedule still plain Frappe checks). One helper: fence + own_line -> ignore_permissions, used by every write. Also swap_shift/delete_shift_schedule_assignment still refuse a supervisor's cross-company line (ceiling marker in insert_shift).
Review b4e7adb81 note: _refuse_worked_day reads calendar day; safe direction only (a night OUT after midnight makes the NEXT day look worked = over-refuse; an IN is always on its own day), so no miss. Revisit if HR reports a wrong "Ask HR".

## Update 5 Oct 2026 (change_shift_from, 12fff2dd5..e0f1f31ea)
roster.py is now 11 fixes/90d. `change_shift_from` is ~100 lines in the endpoint: move the "what was worked" reads (Attendance, Employee Checkin by time, Employee Checkin by shift_start) and the write set into hrms/utils/shift_change.py as one tested helper; the endpoint stays a thin fence + call. Reviewer (3 passes) asked for it; no Critical found.

# Ticket: approval.py hotspot (27 fixes/90d)
decide / decide_many / get_decision_actions / _approve_would_refuse / _decision_access all re-derive "may this caller act on this request and would it be refused". decide_many (5 Oct 2026) deliberately calls decide() and adds no rule, so it stays safe, but each new caller needs the same savepoint + lost-transaction handling. One helper owning "run decide for one item inside a savepoint and classify the outcome" would serve decide_many and any future batch (reject, cancel). Also: after a savepoint rollback Frappe keeps the item's after_commit callbacks queued (frappe/database/database.py rollback(save_point=) does not reset them). Reviewed safe today (PWA push re-reads the row, email flush re-reads the queue, realtime is content-free) but day_remark callbacks were not confirmed to re-read state.

## Update 7 Oct 2026 (alpha.39: ee44ec9fc, 29a84584a, 86d028814, 0c799c0bd, 874619e77) — 15 fixes / 90 days
- update_shift_assignment now takes four optional fields (NOT_SENT) plus three refusal rules and the
  marker clear, about 80 lines in the endpoint. Move "what changed, what is refused, which markers go"
  into one tested helper; the endpoint becomes fence + call.
- `own_line = employee in rostered_employees(...)` is now derived five times (insert_shift, set_day_type,
  _clear_day_markers, break_shift, swap). One "may this caller touch this row" helper.
- Day Type rules live in three places: NO_SHIFT_DAY_TYPES (roster_day.py), _valid_day_type (roster.py),
  ROSTER_DAY_TYPES (ot_calculation.py). One module.
- db_set / db.set_value paths skip Frappe's docstatus check: update_shift_assignment guards it now;
  insert_shift's neighbour merge (db.set_value, docstatus != 2) still includes drafts.
- The no-shift Day Type message is written twice (set_day_type and RosterDay.validate): one helper. Schedule this ticket before the next roster.py fix.
- The "did the Day Type change" decision (old_day_type, markers cleared) in update_shift_assignment belongs inside the planned helper too (review of 28fd9beeb).
