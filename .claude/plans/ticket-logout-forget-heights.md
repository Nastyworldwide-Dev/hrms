# Ticket: logout forgets remembered placeholder heights
Review of bcfbeaa8e/d612c8d07 (27 Oct 2026): utils/placeholderHeight.js stores `hrms:ph:<block>:<email>` in localStorage. Logout does not remove them, so a shared phone keeps the previous person's email in two keys (the heights themselves reveal only roughly how much work they had).
Ready: `forgetAllHeights()` (tested). Change: one line after `clearPersonalCaches(session.user)` in frontend/src/data/session.js logout onSuccess, plus loading the helper in frontend/tests/personal-cache-isolation.test.mjs. Patch saved at /tmp/session-forget.patch.
Blocked by: commit gate marks frontend/src/data/session.js as an auth path (risky tier: plan + owner approval).
