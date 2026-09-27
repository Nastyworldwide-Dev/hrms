CLASS: the notifications feed repeated one person's same request many times, one row each
hrms/api/__init__.py mark_notifications_as_read — same-root (new: names AND caller, POST, max 500)
frontend/src/utils/foldNotifications.js — same-root (new: fold by from_user + kind, newest leads)
frontend/src/views/Notifications.vue — same-root (fold rows with a count, iOS disclosure, fold read in one call)
frontend tests nothing-loose / notifications-feed / notifications-plain — same-root (updated to fold rows; rules unchanged)
hrms/api/__init__.py _incomplete_ot_days, hrms/sync/lone_in_closer.py zip — lint fix (strict=True; equal lengths by construction)
