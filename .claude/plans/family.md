CLASS: an approval that has two doors. Check-ins outside the area were decided
on their own page, reached from More, Profile, Home and notifications, while
every other request waited on the Approvals page (owner ruling 23 Sep:
approvals appear only where they can be done; AUDIT-PLAN Approvals row).

Doors into RemoteApprovals and their verdicts:
frontend/src/views/More.vue — same-root, row removed (AUDIT-PLAN More: cut Remote approvals).
frontend/src/views/Profile.vue — same-root, row now "Approvals" -> Approvals.
frontend/src/components/NeedsYou.vue — same-root, row -> Approvals, words "check-in(s) outside the area".
frontend/src/utils/notifications.js — same-root, every check-in notification -> Approvals.
frontend/src/router/index.js — same-root, /remote-approvals redirects to /approvals (saved links).
frontend/src/data/navItems.js — same-root, More tab lights on /approvals.
frontend/src/views/RemoteApprovals.vue — deleted; its queue, decide sheet and "Decided by you" history live on Approvals.
