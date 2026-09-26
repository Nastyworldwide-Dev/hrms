CLASS: the PWA's service worker was served from a folder that cannot control the app, so nothing worked offline
hrms/www/service_worker.py — same-root (new: serves the built sw.js at /hrms/sw.js, no-cache, Service-Worker-Allowed /hrms)
hrms/hooks.py website_route_rules + page_renderer — same-root (route /hrms/sw.js ahead of the app catch-all)
frontend/src/main.js register — same-root (URL /hrms/sw.js, scope /hrms)
frontend/vite.config.js VitePWA — same-root (registerSW names the same worker: buildBase /hrms/, scope /hrms)
frontend/public/sw.js — same-root (network-first route for /hrms pages; precache unchanged)
frontend/src/utils/frappe-push-notification.js — not-affected — takes the registration main.js hands it; push keeps working off the same worker
frontend/src/components/UpdatePrompt.vue — not-affected — uses registerSW, now pointed at the same worker
