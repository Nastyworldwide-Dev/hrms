# Every way a person leaves forgets the remembered heights (owner approved the logout fix 27 Oct 2026)

Security review of e23b473b8: only the explicit Log out ran forgetAllHeights. Same approved change,
covering the two other ways a person leaves a shared phone.

## FLOW
- frontend/src/utils/personalCache.js sessionEnded(): forgetAllHeights() beside clearCachedPages().
- frontend/src/data/session.js login success: forgetAllHeights() beside clearCachedPages().
- checkin.pendingTap:<employee> (short-lived, cleared on success) -> ticket, not this change.

## MOCKUP: NOT NEEDED (no screen changes)

## EXPECTED OUTPUT
- After a session ends on its own, or a new login on the same phone, no `hrms:ph:` key remains.
