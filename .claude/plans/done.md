GOAL: no page can sign a person's phone up for, or off, their notifications by making the browser visit a link.
DONE WHEN: subscribe/unsubscribe accept POST only; the PWA sends POST + CSRF with the token in the body.
CHECK: bench: GET 403, POST without CSRF 400, POST with CSRF reaches the handler; hrms/api/test_push.py + frappe-push-notification.test.js green
