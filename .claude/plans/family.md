# Family — fix(attendance): Fix days rebuilds through approved requests and keeps them (21 Sep 2026)
CLASS: two guards (the screen's day block and the engine's day protection) refused any day covered by an approved OT / Attendance Request, so HR had to cancel a request before the row could be recomputed; the owner ruled the request stays and the row is rebuilt
Changed symbols: attendance_fix_day.day_block_reason/_day_block/_rebuild (requests_ok), _paid_day, _leave_cover, _requests_on (new); attendance_fix_days (requests_kept, keeps_the_day); day_remark.remark_day/_remark_owning_the_day/_remark_once (requests_ok threaded); attendance_recovery._day_protection (requests_ok, _paid, _leave_cover); remote_checkin_request_hooks._repair_financial_dependency (requests_ok skips the OT Request clause only); leave_cover.request_covered_days(doctypes).
Every other caller of each changed function passes the default (verifier grep, 18 call sites listed) — behaviour byte-identical outside fix_days.
hrms/api/attendance_fix_day.py:rebuild_day / single actions not-affected — default False; the per-day screen still refuses request days as before
hrms/utils/attendance_recovery.py:protected_reason not-affected — still holds a submitted AR row; fix_days cancels that row first, so the engine sees none (ordering, noted)
hrms/hr/doctype/attendance/attendance.py:on_cancel not-affected — unlinks punches only; no hook touches the request
hrms/hr/doctype/attendance_request/attendance_request.py:on_cancel not-affected — cancels only rows linked to itself; the rebuilt engine row carries no link
Paid days: Salary Slip and Overtime Details still refuse (money); approved-unpaid OT is kept and the row's OT hours recomputed from punches.
