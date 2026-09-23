CLASS: server datetime rendered on the wrong clock (PWA boot had no site zone; lists parsed on device clock)
hrms/www/hrms.py:get_boot same-root (sends sysdefaults.time_zone)
frontend/src/utils/siteTime.js:siteTimeZone same-root (already reads sysdefaults.time_zone; now populated)
frontend/src/components/*RequestItem.vue since() same-root (siteTime)
frontend/src/components/ExpenseClaimItem.vue since() same-root
frontend/src/components/EmployeeCheckinItem.vue same-root
frontend/src/components/NowBar.vue elapsed same-root
frontend/src/views/announcements/List.vue when() same-root
frontend/src/components/ListView.vue:417 same-root ("HH:mm a" printed "18:31 pm")
frontend/src/views/Notifications.vue:100 not-affected — already siteTime; fixed by boot
frontend/src/utils/formatters.js formatTimestamp ticket alpha5-S9 — date-format unification slice
frontend/src/views/helpdesk/HelpdeskList.vue, issues/IssueList.vue, HRIssueBoard.vue, sop/* ticket alpha5-S8 — rows rewritten in the Help/SOP redesign slice
frontend/src/components/LateCheckoutDialog.vue, CheckInPanel.vue not-affected — compare device-now to a datetime-local input the user typed on the device clock
