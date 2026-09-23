CLASS: a sheet with no visible way to close it except the drag.

Call sites: frontend/src/components/glass/GModal.vue — same-root, fixed (Close in the head). All 16 GModal users (DaySheet, GActionSheet, GConfirm, CheckInPanel, RemoteCheckinDialog, StrictRejectionDialog, LateCheckoutDialog, PushNotificationPrompt, InstallPrompt, InvalidEmployee, Login, ListView, More, TeamRoster, Approvals, DesignSpecimen) render through it — same-root.
