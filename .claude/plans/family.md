CLASS: a batch loop that keeps going after a lost transaction (deadlock 1213 / lock timeout 1205) reports approvals that were rolled back; and a batch that takes row locks in client order can deadlock against another batch. The fix reuses the ONE existing lost-transaction test (hrms/utils/offshift_punch_heal._lost_transaction) and sorts the batch; it changes no existing caller.
hrms/api/attendance_master_edit.py:206 not-affected — calls the same helper, which is unchanged; this commit only adds a new caller (hrms/api/approval.py)
hrms/api/attendance_master_edit.py:247 not-affected — same helper, unchanged
hrms/sync/lone_in_closer.py:433 not-affected — same helper, unchanged
hrms/utils/attendance_health.py:103 not-affected — same helper, unchanged
hrms/utils/attendance_health.py:177 not-affected — same helper, unchanged
hrms/utils/attendance_recovery.py:1106 not-affected — same helper, unchanged
hrms/utils/attendance_recovery.py:2859 not-affected — same helper, unchanged
hrms/utils/attendance_recovery.py:2911 not-affected — same helper, unchanged
hrms/utils/attendance_recovery.py:3176 not-affected — same helper, unchanged
hrms/utils/attendance_recovery.py:3312 not-affected — same helper, unchanged
hrms/utils/attendance_recovery.py:3321 not-affected — same helper, unchanged
hrms/api/approval.py:decide_many same-root (fixed here: aborts the batch on a lost transaction)
hrms/api/approval.py:_bulk_items same-root (fixed here: fixed order, revision required)
hrms/api/roster.py:change_shift_from not-affected — no loop that continues past a per-item failure; one request, one transaction, no savepoints
