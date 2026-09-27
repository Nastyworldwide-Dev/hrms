CLASS: a state-changing endpoint accepting GET (CSRF skipped); the 18-endpoint sweep f38f46320 missed these two because they are overrides of Frappe's own names
hrms/api/push.py:25 same-root — subscribe POST only
hrms/api/push.py:32 same-root — unsubscribe POST only
frontend/src/utils/frappe-push-notification.js:291 same-root — subscribe sends POST + CSRF, token in body
frontend/src/utils/frappe-push-notification.js:318 same-root — unsubscribe the same
hrms/hooks.py:777 not-affected — routes the framework names here, unchanged
