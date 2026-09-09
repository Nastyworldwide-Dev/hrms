# family.md — push relay: stored credentials reused by a cloned site

CLASS: a CACHED CREDENTIAL is trusted without checking WHO it identifies.
`frappe.push_notification.PushNotification._get_credential` returns the stored
api_key/api_secret whenever both are present; a site built from a copy of
another site inherits the source's pair and every relay call goes out as the
source site's API user while naming this site. The relay refuses with
PermissionError on Notification User and every subscribe and push send fails.

Changed: hrms/utils/push_relay.py (new: relay_call, reset_relay_credentials),
hrms/api/push.py (new: subscribe/unsubscribe wrappers), hrms/hooks.py
(override_whitelisted_methods), hrms/hr/doctype/pwa_notification/
pwa_notification.py (send_push_notification via relay_call).

Call sites / importers of what changed, with verdicts:
- frappe.push_notification.subscribe / unsubscribe (called by name from
  frontend/src/utils/frappe-push-notification.js:284,311) — same-root: routed
  to hrms.api.push.* by override_whitelisted_methods; heals on first refusal.
- hrms/hr/doctype/pwa_notification/pwa_notification.py send_push_for (after
  commit job, hooks: PWANotificationsMixin producers) — same-root: the send
  now goes through relay_call; the surrounding try/except still logs any
  failure that survives the one retry.
- hrms/utils/readiness.py:360 — not-affected: reads
  enable_push_notification_relay only, never the credentials.
- hrms/api/__init__.py are_push_notifications_enabled — not-affected: same,
  reads the enable flag only.
- frappe relay topic functions (add_topic, subscribe_topic, ...) — not
  affected: hrms never calls them.
- nasty-live (the source site) — not-affected: its stored credentials ARE its
  own; the relay accepts them; relay_call never fires there.
- hrms/subscription_utils.py — not-affected: its identity comes from
  frappe.conf.sk_hrms (site_config, which a DB clone does not carry) and its
  only caller is gated on a *.frappehr.com hostname we never have.
- docs/glass/audit/2026-09-08-notification-probes.py — not-affected: an audit
  script that patches _send_post_request wholesale; excluded from the scan.
- OPEN ASSUMPTION (reviewer): what the relay's auth.get_credential does for an
  endpoint that is already registered is unverified (relay source not
  readable). Only reachable through a relay-side fault on a healthy site, and
  a refused re-registration rolls back, leaving the old pair intact.
