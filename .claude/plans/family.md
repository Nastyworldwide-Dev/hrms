CLASS: a scrolling screen with no pull-to-refresh (alpha.35 S2 left one: HR's issue board on the Help page's HR pill).
frontend/src/views/issues/HRIssueBoard.vue same-root (reloads issues; sits in the Help page's ion-content like IssueList)
frontend/src/views/issues/IssueList.vue not-affected — already wired in alpha.35; v-if/v-else with this board, never both
frontend/src/views/helpdesk/HelpdeskHub.vue not-affected — its refresher is IT pill only
frontend/src/views/Profile.vue, More.vue not-affected — plan ruling 5: skipped on purpose
