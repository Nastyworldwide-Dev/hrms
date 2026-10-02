GOAL: plain staff clicking Nadi on Desk land in the PWA (/hrms) instead of "No permission for Page" (owner ruling b, 2 Oct 2026).
DONE WHEN: a user who cannot open the Shift & Attendance workspace gets Nadi tile + app-switcher route /hrms; HR and Shift Supervisor keep /desk/shift-&-attendance.
CHECK: PYTHONPATH=. python3 hrms/tests/test_desk_boot.py; fresh.local boot as plain Employee -> ['/hrms'], as Shift Supervisor -> ['/desk/shift-&-attendance'].
