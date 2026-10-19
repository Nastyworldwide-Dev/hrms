# Nadi 2.0.0-alpha.57 — plan (draft, 19 Oct 2026)

Theme: bug fixes and quality of life. No new features. Sources: open follow-ups
from alpha.48–56 (progress.md), .claude/plans/ticket-*.md, memory notes.

## Bugs
1. Check-in button placeholder jumps at large text.
   CheckInPanel.vue:86 GSkeleton height="48px"; the real button grows with
   Dynamic Type (alpha.56). Fix: size it in rem / the button's own min-height.
2. Compact buttons clip at large text.
   glass-components.css:455 .g-btn--compact white-space: nowrap. Fix: allow
   wrap above the default size, keep nowrap at default.
3. A login with no Employee record lands on a broken Home (Mia, alpha.54).
   navigationGate lets it through. Fix: viewer-only start page (More) for a
   login with a viewer role and no Employee; others see the existing "not linked" page.
4. Announcements may hide from other companies (same class as the SOP bug).
   Check first: does a Nadi-made announcement take HR's company from a Company UP?
   Reproduce on fresh.local as HR with a Company UP. Fix only if red.

## Quality of life
5. Receipt / time-slip file row: show a tick and "Tap to replace" after upload.
6. Time-slip sheet: the late hint for a night shift after midnight.
7. Status pills read aloud as a status (role="status") for VoiceOver.

## Clean-up (no user change)
8. 7 prettier errors in views/attendance/AttendanceDownload.vue (lint red).
9. test_sop_document.py: 11 tests red since before alpha.50 (identity stub).
   ticket-sop-document-tests-identity-stub.md.

## Needs the owner's word (not in the release until answered)
- Leave email: send it up the line when no approver is named? (ticket-leave-email-not-routed-up-the-line.md)
- May an admin-only login correct requests? (ticket-correction-roles-name-system-manager.md)

## Not in this release
- Text above 135% screen by screen (large; own release).
- Hotspot refactors: team.py (24 commits/90d), sop.py, approval.py.

## DONE WHEN
- Each item: a test red on HEAD, green after; frontend tests per file; lint 0.
- 1–2: page-audit at Text Size +2 shows no jump, no clipped button.
- 3: a viewer with no Employee opens Nadi on More, no fetch loop.
- One commit per cause; release.sh tag v2.0.0-alpha.57; no migrate expected.
