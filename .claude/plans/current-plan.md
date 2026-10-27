# Logout forgets remembered placeholder heights (owner approved 27 Oct 2026)

Ticket: .claude/plans/ticket-logout-forget-heights.md. Review of bcfbeaa8e/d612c8d07.

## FLOW
- frontend/src/data/session.js logout onSuccess: after clearPersonalCaches(session.user), call
  forgetAllHeights() (utils/placeholderHeight.js, tested) so no `hrms:ph:<block>:<email>` key stays
  on a shared phone.
- frontend/tests/personal-cache-isolation.test.mjs loads utils/placeholderHeight.js into its vm
  context (it evaluates session.js by hand).
- Test: a source test that logout calls forgetAllHeights after clearPersonalCaches.

## MOCKUP: NOT NEEDED (no screen changes; logout behaves the same for the person)

## EXPECTED OUTPUT
- After logout, localStorage has no key starting `hrms:ph:`; other keys (install prompt) remain.
- personal-cache-isolation and session tests stay green.
