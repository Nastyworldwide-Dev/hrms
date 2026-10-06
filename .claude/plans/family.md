CLASS: a scrolling screen with no pull-to-refresh: the person pulls, nothing happens, and stale data stays until they leave the screen. Six screens had GPullRefresh; seven did not.
frontend/src/views/Notifications.vue same-root (feed + unread count)
frontend/src/views/team/TeamDashboard.vue same-root (team status + managers)
frontend/src/views/team/TeamRoster.vue same-root (roster + managers)
frontend/src/views/attendance/Dashboard.vue same-root (calendar.refresh + month dots + shifts)
frontend/src/views/leave/Dashboard.vue same-root (balance + my leaves)
frontend/src/views/issues/IssueList.vue same-root (my issues; sits in the hub's ion-content)
frontend/src/views/helpdesk/HelpdeskHub.vue same-root (IT pill only, so one pull is never answered twice)
frontend/src/views/helpdesk/HRIssueBoard.vue ticket S2-followup — HR users on the HR pill: board owns its issues privately; wire it next release
frontend/src/views/Profile.vue, More.vue not-affected — plan ruling 5: skipped on purpose
