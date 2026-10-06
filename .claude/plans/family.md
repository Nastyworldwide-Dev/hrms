CLASS: an update that only arrives when nobody is looking for it. A new build was APPLIED only while the app is hidden (owner rule 30 Sep: no popup, never under a form), but nothing ASKED for one: the browser looks for a new sw.js on a page load and about once a day, so a phone that keeps Nadi in memory could run an old build for days after a deploy.
frontend/src/data/swRegistration.js:setRegistration same-root (fixed here: asks at launch)
frontend/src/data/swRegistration.js:onVisibilityChange same-root (fixed here: asks when the app comes back, at most once per 30 minutes; a failed ask is one console line)
frontend/src/data/swRegistration.js:applyWhenHidden not-affected — a found build still waits for the app to be out of sight
frontend/src/main.js:register not-affected — registers once and hands the registration over, unchanged
frontend/src/router/stale-chunk.js not-affected — the reload-on-missing-chunk rescue stays as the safety net
