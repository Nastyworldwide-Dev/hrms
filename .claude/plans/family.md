CLASS: a display line built from a stored sentence that keeps only the parts it knows, so a part the writer added is silently dropped. The rejection notice carries "Reason: ..." (f5941bed4) but the feed parser read the sentence up to the first full stop and showed nothing after it, so an employee was told Rejected and still never saw why. The parser now decodes entities, splits the reason off, and the row shows it after who and when.
frontend/src/utils/notificationLine.js:notificationLine same-root (fixed here: returns `reason`, only for a Rejected decision sentence)
frontend/src/views/Notifications.vue:groups same-root (fixed here: the row's second line ends with the reason)
frontend/src/utils/notificationLine.js:lineFor not-affected — internal; every caller goes through notificationLine
hrms/mixins/pwa_notifications.py:notify_approval_status not-affected — the writer; already appends the escaped reason (f5941bed4)
hrms/api/push.py:none ticket push-body-entities — the push body strips tags but not entities, so a reason with & or a quote may show as &amp; (next commit, server side)
frontend/src/views/Approvals.vue:none not-affected — reads the approvals list (reason from approvals_list), not the notification sentence
