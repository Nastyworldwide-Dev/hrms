CLASS: a Fix attendance action that refuses, or silently does nothing to, a pre-cutover punch (synced_from_instance)

Instance: owner report 25 Sep 2026, Norazlin 19-20 Aug: "The engine could not read this day: no counted taps", then Save & rebuild refused the ticked pair (punches mirrored from the old ERP; the 21 Sep one-button rewrite dropped the separate claim step).

Sites (every _tap() caller in hrms/api/attendance_fix_day.py):
- save_day ticked taps — same-root (taken over when the instance is unlocked; locked -> refused naming the site)
- move_tap — same-root (same rule)
- _screen / get_day suggestion — same-root (reads the day through _claimable_view)
- save_day unticked (delete) taps — not-affected: already mirrored_ok + _mirror_delete_allowed (G8)
- claim_tap — not-affected: is the take-over itself
- pair_taps / ignore_tap / restore_tap / add_tap — not-affected: not reachable from the one-button dialog (21 Sep rewrite); their refusal stays
- _finish — same-root, second cause: a ticked pair the engine marked NO row for (shift auto attendance off) answered "done"; now refused with the engine's reason and rolled back

Locked: hrms/tests/test_attendance_fix_day_save_day.py (+6). Verified on the bench: mirrored pair -> Present 9.09 h; shift auto attendance off -> refused with the reason, nothing written.
