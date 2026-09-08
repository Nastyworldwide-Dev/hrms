# Calendar and late attendance follow-up

Scope authorized by 360-fixes.md; risky, separate reviewed commits. Preserve Hafiz's draft reader and submitted precedence. No historical mass update or new Present derived solely from a punch.

## CAL-REFRESH
Confirmed AttendanceCalendar creates one month-independent cached resource; month watcher fetches, but no Attendance realtime subscription, mobile view re-entry refresh, explicit refresh action, or stale-response ownership. CheckInPanel explicitly reloads its own checkins only after successful punches. Attendance dashboard claim summary also never refreshes on attendance/OT decisions.

Executor owns AttendanceCalendar.vue, data/attendance.js if needed, minimal CheckInPanel success invalidation, attendance/Dashboard.vue and real component tests. Use existing personalCache/realtime helpers, no global unscoped account data. Establish per-user/month request ownership; old responses must not replace the selected month. Refresh after committed punch response, Attendance list update and cached Ionic view re-entry/reconnect; detach handlers without affecting other subscribers. Reuse installed lifecycle APIs. Avoid duplicate reload storms. Keep old month data from being drawn under the new month title, and expose usable retry on failure, including errors after earlier data.

Pending feedback must distinguish recorded punch from processed Attendance, including remote Pending, Rejected, missing OUT and unprocessed valid pairs. First trace existing employee checkin list/status feedback. Add narrowly scoped, permission-fenced data only if current payload cannot explain the state; no fabricated Present, no employee names/coordinates in logs. Existing calendar events API dictionary shape must stay compatible unless every caller is deliberately migrated. Tests: old month slow response, selected month error/retry, success event without socket, Attendance decision event, re-entry, account isolation, unmount cleanup.

## ATT-PROVISIONAL
Confirmed employee_checkin.create_attendance uses raw db.set_value for provisional auto-Absent and existing half-day updates; this skips Attendance.validate/set_overtime and leaves OT/band fields stale. Whole-shift trusted repair already goes through canonical lifecycle and must be preserved. Inspect submitted-row update rules and financial/manual/mirrored safeguards before choosing cancellation/amendment or controlled supported update. No blanket ignore_validate, no manufactured admin authority, no commit in helper. Persist all hour/band fields coherently; rollback everything on failure. Preserve legitimate leave half-day semantics. Verify native real row reload, punch linkage, valid nonworking pair Present/no flags, weekday minimum, protected rows, financial guard and rollback. Do not put a new SQL-only OT calculator beside canonical calculation.

OT worker owns ot_calculation/holiday resolver/index; coordinate rather than overwrite. Precision six fields changes only storage. Root integrates only reviewed paths against current root.

NEXT: Assign CAL-REFRESH then ATT-PROVISIONAL to location worker after geofence audit review completes.
