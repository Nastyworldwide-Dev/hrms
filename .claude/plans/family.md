# Family — fix(attendance): every rebuild is guarded and logged; typed rows and HR's press are honoured (21 Sep 2026)
CLASS: rebuild protection was inconsistent — the owner hold asked a classifier that could not answer (rows read without owner/versions/punches), the never-worse guard compared a tap list to itself, three rebuild paths bypassed the guard entirely and wrote no log, and the guard rolled back HR's own deliberate lowering while Fix Day's inline deadlock retry rolled back HR's taps and still logged ok
Changed symbols: attendance_recovery.owner_hold/_is_hr_hold/typed_by_a_person (new), evidence_shrank/_live/before_rebuild, _rebuild_under_guard (hr_asked, action, source), _fix_rostered_day; day_remark.remark_day (inline), _remark_once (guarded, logged), _retire_unmarkable_rows (logged); attendance_fix_day.NOT_APPLIED/_finish; HR Day Fix Log source Select.
hrms/utils/attendance_auto_recovery.py:run_nightly same-root — every nightly step now reaches a guarded, logged rebuild; test_attendance_auto_recovery 26 green
hrms/utils/attendance_endgame.py not-affected — its rebuilds already went through guarded_rebuild; the duplicates step's bare re-mark now lands in the guarded job path (G4c) — 43 green
hrms/sync/erp_backfill.py not-affected — already guarded; automatic callers still roll back a lowering (test_an_automatic_caller_is_still_rolled_back)
hrms/sync/lone_in_closer.py not-affected — reads owner_hold; typed rows now hold (29 green)
hrms/api/attendance_master_edit.py not-affected — writes auto_attendance=0 rows, which the stopgap now protects until Release 2 removes the flag
hrms/public/js/fix_day.bundle.js not-affected — the "held" rendering branch is unreachable for HR's own press now (a held day answers ok + log); harmless, removed in Release 2
Stopgap note: pre-1-Sep and mirrored rows still carrying auto_attendance=0 that relabel_system_rows has not relabelled re-enter the hold; accepted until Release 2.
