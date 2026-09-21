# Family — fix(attendance): the absent sweep locks the person and skips anyone with no calendar (21 Sep 2026)
CLASS: a writer without the employee lock racing the nightly, and a rule that marked rest days and public holidays Absent when the calendar it needed was missing
Changed symbol: shift_type.mark_absent_for_dates_with_no_attendance (lazy lock_employee_row once per employee; holiday_list_covers gate per date, one warning per employee).
hrms/hr/doctype/shift_type/shift_type.py:_process same-root — the same lock taken per punch group; the sweep now matches it; lock lives until the batch commit (pre-existing pattern, EMPLOYEE_CHUNK_SIZE)
hrms/hr/doctype/shift_type/shift_type.py:get_holiday_list not-affected — unchanged: shift list if it covers, else the dated resolver
hrms/utils/holiday_list.py:holiday_list_covers same-root — reused; an ended fallback calendar reads as none (owner ruling: skip, not Absent)
hrms/utils/readiness.py not-affected — already names employees with no calendar (24767e60d); the sweep logs one warning and does not notify again
hrms/tests/test_pairing_rule_table.py:row 9 same-root — harness gained the two seams (covers → True, lock → no-op)
