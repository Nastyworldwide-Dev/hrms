# Plain staff: Desk Nadi tile opens the PWA (owner ruling b, 2 Oct 2026)

## FLOW
frappe.sessions.get -> extend_bootinfo hook hrms.desk_boot.send_plain_staff_to_pwa(bootinfo)
-> "Shift & Attendance" not in bootinfo.workspaces["pages"] (Frappe's own allowed list)
-> Nadi desktop icon link + app_data[hrms].app_route = /hrms. HR / Shift Supervisor unchanged.

## MOCKUP: NOT NEEDED (no new screen; a tile's link changes for one group)

## EXPECTED OUTPUT
- Plain Employee: Nadi tile and app switcher open /hrms (the Nadi app).
- Shift Supervisor, HR: Nadi opens /desk/shift-&-attendance as before.
- Other apps' tiles untouched.

APPROVED: owner, 2 Oct 2026 — "b, send plain staff to the PWA"
