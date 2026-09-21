# Family — fix(attendance): Fix attendance refuses a locked mirrored punch up front; the dialog applies the engine's labels (21 Sep 2026)
CLASS: (1) a guard that lived in a doc-event hook (on_trash block_mirrored_writes) fired half-way through save_day, after the rows were cancelled; (2) the dialog showed the device's IN/OUT label instead of the engine's suggested role, so the pre-ticked pair read "IN after OUT".
hrms/api/attendance_fix_day.py same-root — _mirror_delete_allowed asked before any write (G8)
hrms/public/js/fix_day.bundle.js same-root — suggested role is the pre-applied label; State header; row line without ids
hrms/sync/write_block.py not-affected — read only (_instance_unlocked)
hrms/api/attendance_fix_day.py undo_fix / _delete_tap not-affected — same delete path, now unreachable for a locked instance
hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js same-root — pins updated
