CLASS: moving the service worker changed what its relative URLs mean
frontend/public/sw.js precacheAndRoute — same-root (fixed: entries re-based onto /assets/hrms/frontend/)
frontend/src/main.js retireOldWorker — same-root (new: unregister the pre-alpha.12 worker at /assets/hrms/frontend/)
frontend/src/main.js movePushToAppWorker — same-root (new: re-subscribe push once for people who had it on)
frontend/public/sw.js NavigationRoute nadi-pages — not-affected — absolute allowlist, network first; a cached page holds only site-level boot data (hrms.py get_boot)
