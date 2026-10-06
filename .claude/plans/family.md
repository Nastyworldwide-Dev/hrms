CLASS: one action, several readers of its result, and only some of them told. A saved punch reloaded the punch list, but the status line ("Done for today" / "Working") and the week line read other resources that nothing reloaded, so the Today card contradicted itself ("Done for today" beside a "Check out" button) until the page was reloaded. Reproduced in a real browser on the test site, 6 Oct 2026.
frontend/src/components/CheckInPanel.vue:refreshAfterPunch same-root (new: ONE function that reloads the punch list, the stale-IN banner, the status line and the week line; allSettled so one failing read stops none)
frontend/src/components/CheckInPanel.vue main punch / lost answer / RemoteCheckinDialog / LateCheckoutDialog / realtime list_update same-root (fixed here: all five paths call it)
frontend/src/components/NowBar.vue not-affected — it reads nowResource, which the function now reloads
frontend/src/components/HomeWeek.vue not-affected — reads homeWeek, same
frontend/src/views/Home.vue:refresh not-affected — pull-down already reloads these; its own handler never ran (next commit)
hrms/api/attendance_fix_day.py ticket stale-status-after-fix-day — HR's "Fix a day" probably leaves the same stale Today line for the employee; not reproduced
