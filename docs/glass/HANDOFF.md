# HANDOFF
prompt:   7.3 (anatomy audit — read-only)
status:   done, nothing changed
commit:   see below on nz-glass
files:    docs/glass/anatomy-audit.md
verify:   read the audit; findings are template-derived, not browser-observed
flags:    FOLLOWS 4 — Sign in, Check in, Issues (staff), Issue board
          DIVERGES NOT RECORDED 4 — Home, Leave, Attendance, Overtime; KPI has one more
          THE LOGIN PATTERN REPEATS 3× — Home, Leave and Attendance are re-skinned inside
          two-column lg: grids no anatomy describes, contradicting §20.3's single 720px
          column. Invisible below lg:, which is why three batches passed over it. Needs a
          ruling: defect, or an unwritten desktop pattern
          OVERTIME IS THE DEEPEST — field order comes from get_doctype_fields, so the
          anatomy cannot be satisfied by styling at all. GNotePanel has ZERO consumers;
          §10.2 #22's eligibility hint does not exist in the app. All 8 form screens share
          the mechanism
          ATTENDANCE stack order wrong on mobile too (action list after the request lists,
          from 5.3 flattening in place), plus a duplicate order-6 with order-5 unused
next:     rule on the two-column layouts, then fix Attendance's order and Overtime's note
