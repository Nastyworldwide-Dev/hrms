# Plan: the app installs again (owner, 27 Oct 2026: "check why android user cant install pwa both android and iphone")

## GOAL
/hrms/manifest.webmanifest returns the built manifest, so Android Chrome offers install and an iPhone's
Add to Home Screen saves the app with its name and icon.

## FLOW
page <link rel="manifest" href="/hrms/manifest.webmanifest"> -> hooks.py website_route_rules (own rule, ahead of
/hrms/<path:app_path>) -> ServiceWorkerPage.can_render (MANIFEST_ROUTE) -> render -> built
hrms/public/frontend/manifest.webmanifest as application/manifest+json, Cache-Control no-cache

## MOCKUP: NOT NEEDED (server route only; no screen changes)

## EXPECTED OUTPUT
- curl /hrms/manifest.webmanifest -> 200 application/manifest+json (was 200 text/html, the app page)
- Chrome CDP Page.getAppManifest: errors [] (was "Line: 1, column: 1, Syntax error"); getInstallabilityErrors: []
- hrms/www/test_service_worker.py: 8 passed (route test and manifest tests red first)

## RISK
One new route rule for one exact path, before the catch-all; every other /hrms path unchanged. Rollback: drop the rule.
