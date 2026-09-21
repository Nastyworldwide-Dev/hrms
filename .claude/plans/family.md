# Family — fix(pwa): site timezone read from the real bootinfo shape (21 Sep 2026)
CLASS: a boot value assumed to be a string is an object — frappe.boot.time_zone is {system, user} (frappe/boot.py set_time_zone); dayjs.tz() threw on it in every request list and on Notifications.
Changed: frontend/src/utils/siteTime.js siteTimeZone() (sysdefaults.time_zone → time_zone string → time_zone.system → default) + try/catch fallback in siteTime().
frontend/src/components/RequestPanel.vue same-root — caller of siteTime, fixed here
frontend/src/views/Notifications.vue same-root — caller of siteTime, fixed here
frontend/src/utils/__tests__/siteTime.test.js same-root — mock now uses the real bootinfo shape
grep -rn "boot.time_zone\|boot?.time_zone" frontend/src → only siteTime.js; no other reader of the object
