CLASS: text written for one surface (escaped HTML in a Text Editor field) reused on another (a phone lock screen, a feed row) without translating it. The rejection reason is stored escaped, the framework push strips tags but not entities, so "Tom & Jerry" reached the phone as "Tom &amp; Jerry"; and an unbounded reason made a notice as long as the approver typed. The push body is now stripped then decoded in ONE place, and the notice cuts a long reason (the full text stays on the request).
hrms/hr/doctype/pwa_notification/pwa_notification.py:send_push_notification same-root (fixed here: body goes through push_body, strip_html off so it is not stripped twice)
hrms/mixins/pwa_notifications.py:notify_approval_status same-root (fixed here: reason cut at REASON_NOTICE_MAX, ellipsis)
hrms/mixins/pwa_notifications.py:notify_approver not-affected — message is built from names and a doc name, escaped by bold(); no free text from a user
hrms/hr/doctype/pwa_notification/pwa_notification.py:get_notification_link not-affected — builds a URL, not text
frontend/src/utils/notificationLine.js:notificationLine not-affected — decodes entities itself (1ad6e6c7d)
hrms/api/approval.py:decide not-affected — records the FULL reason as a Comment; only the notice is cut
