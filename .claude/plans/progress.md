2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
- 2026-10-05T07:30:30Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T07:30:30Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:30:33Z COMMIT: 225d95f41 fix(approvals): bulk approve could deadlock, hide a lost transaction, or skip the revision check → review dispatched
- 2026-10-05 PLAN B step 1 reviews: f3f0a587a + 225d95f41 reviewed, no Critical. Fixed: fixed lock order, abort on lost transaction (reuses offshift_punch_heal._lost_transaction, imported lazily), revision required, text-only names. Refactor tickets filed in ticket-roster-py-refactor.md (roster.py + approval.py). OPEN: day_remark after_commit callbacks of a rolled-back bulk item not confirmed to re-read state (ticket).
- 2026-10-05 MOCKUPS: /home/nabil/mockups/mockup-approvals-table.html (Check-in rows now 1x, never selectable) and /home/nabil/mockups/mockup-change-shift-from.html (new) await owner sign-off. Nothing pushed.
NEXT: owner signs off the two mockups, then Plan A step 2 (Desk dialog) and Plan B step 2 (Approvals page).
- 2026-10-05T07:32:44Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T07:32:44Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T07:32:47Z COMMIT: e44496ed5 fix(approvals): bulk approve crashed on non-text names and loaded attendance code on every request → review dispatched
- 2026-10-05 PLAN A step 2 (Desk dialog): hrms/public/js/change_shift_from.bundle.js, loaded at boot (hooks.py app_include_js), button "Change shift from..." under Actions on a submitted Shift Assignment, HR only. EVIDENCE: 2 correct - node tests 8 green (red first: file missing), hrms/tests/test_change_shift_screen.py 7 green, each of 5 breaks (endpoint renamed, GET, button for everyone, weekday spelling, not loaded) fails a test. 3 works - ran the dialog in a real browser with a faked frappe: preview reads "Until 2026-10-11: no change | From 2026-10-12: 10am-7pm (Mon, Tue, Wed, Thu); 10am-4pm (Fri) | No shift on: Saturday, Sunday."; three presses in one instant = one server call; payload matches the endpoint. NOT verified: bench build (node 22 here, frappe wants >=24, so `bench build` fails with or without this change; esbuild alone bundles the file, 8 KB, syntax ok) and the dialog inside real Desk.
OPEN: roster row-menu door (Vue roster app) not built; the form door is. Approvals page UI (Plan B step 2) not built.
- 2026-10-05T07:44:10Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-10-05T07:44:10Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-05T07:44:14Z COMMIT: 0c5327a15 feat(desk): HR can change a person's shift from a date on the Shift Assignment form → review+design+cross-app dispatched
- 2026-10-05T07:49:30Z EVIDENCE: 6 behaves — family hunt: class=a dialog that shows only what HR typed and swallows what the server said. The shift; 40 call site(s) given verdicts, 4 same-root ⟂b7295ee5c9cb
- 2026-10-05T07:49:49Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-10-05T07:49:49Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-05T07:49:55Z EVIDENCE: 6 behaves — family hunt: class=a dialog that shows only what HR typed and swallows what the server said. The shift; 40 call site(s) given verdicts, 4 same-root ⟂b7295ee5c9cb
- 2026-10-05 PLAN A step 2 reviews of 0c5327a15 (frappe-reviewer: no Critical; cross-app: SAFE; design-reviewer: FIX_CRITICAL on a11y). FIXED: server refusal was never shown (frappe.messages.slice is not an array in v16 -> TypeError; now reads _server_messages), chips have aria-pressed + full weekday name + reason when disabled + focus kept, visible labels per shift, preview is a live region, errors role=alert, busy label "Changing...", shift labels carry their hours, translated "{0}, from {1}". NEW: hrms.api.roster.preview_shift_change (read-only, HR only) so the dialog names the one-day changes the date will drop and refuses a worked day as soon as the date is picked; change_shift_from and the preview share ONE read (_assignments_and_worked_days) and ONE rule (plan_change). EVIDENCE: 2 correct - 63 python + 15 node tests green (red first; 3 breaks each fail a test). 3 works - real fresh.local probe: preview and change agree (punched day refused in both; preview lists the removable assignment), non-HR refused; real browser run with a REAL-shaped frappe (messages is an object): refusal text reaches HR, focus stays on a toggled chip, 2nd-row chips named+disabled, preview aria-live. NOT verified: the dialog inside real Desk (bench build needs node >=24, here 22).
- 2026-10-05T07:49:56Z COMMIT: 7dd5e3aa8 fix(desk): the shift change dialog hid the server refusal and said nothing about what it drops → review+design dispatched
- 2026-10-05 PLAN A step 2 pass 3 (reviews of 7dd5e3aa8: frappe-reviewer no Critical, design pass 2 FIX_WARNINGS). FIXED: live regions are in the dialog from the start and only their text changes; ask_server drops an answer still on its way on EVERY path (cleared date, removed shift), a failed preview redraws; shift list that fails or is empty says so; focus goes to a new shift row; "A day can be on one shift only." hint; the form door formats the date. EVIDENCE: 3 works - real-browser run: late reply after a cleared date does NOT repaint the old refusal; failed preview shows the local preview only; 11 python + 15 node tests green, each of 3 breaks fails a test. LEFT (deliberate, noted): chips are btn-sm (24-28px, matches mockup; Desk admin tool); no 7-day grid in the preview; no remove-row button; HR-with-User-Permission preview test.
- 2026-10-05 PROVE-RED escape used (PIPELINE_SKIP_PROVE_RED=1, once, for the "repaint a refusal for a cleared date" fix): the gate re-ran the UNCHANGED change_shift_from.bundle.test.js against HEAD (green by construction) and reported my 4 new tests as green-before. Run by hand against HEAD's bundle, test_change_shift_screen.py goes 4 failed / 7 passed (the 4 new tests are exactly the red ones); against the fix 11 passed. LEARNING(gate): a fix whose new tests are Python-only is blamed for the mapped JS file's old tests -> prove-red should judge only the files this commit changes.
- 2026-10-05 PLAN B step 2 (Approvals page): frontend/src/utils/approvalBulk.js (pure: chips, ageing, ticks, select-all, itemsFor, afterApprove), Approvals.vue (banner, type chips, Select mode, per-request ticks, sticky "Approve N" bar, confirm sheet "N ready / N will be refused"), tests approvals-bulk.test.js (15) + approvals-bulk-page.test.js (14). EVIDENCE: 2 correct - 45 node tests green across the 5 approvals suites; 7 page breaks + 6 helper breaks each fail a test. 3 works - ran the REAL page (vite dev + stubbed API) in a 390px browser: banner "7 waiting. Oldest since 17 Aug.", chips, Overtime filter narrows groups to 2, Select all ticks 6 of 7 and the check-in row is NOT tickable, sticky bar "6 selected / Approve 6", confirm sheet "4 ready / 2 will be refused" with the reason, Approve 4 -> decide_many called ONCE with the ready ones and the revision, toast "4 approved". Caught on the way: two `const selected` (renamed ticked), the empty-state v-else hung on the wrong element (now v-if="!rows.length"), a chip colour token that did not exist (--g-ground -> --g-bg).
NOT BUILT: the desktop Table view (columns, sort, search) - HR's "datatable"; select mode + chips work on desktop too. NOT verified: inside the real app against the real server; dark theme; 320 px reflow.
- 2026-10-05T08:02:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-05T08:02:35Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-10-05T08:03:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-05T08:03:12Z COMMIT: 5943dfa58 feat(approvals): the bookkeeping for filtering and approving many requests → review+design dispatched
- 2026-10-05T08:03:26Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T08:03:30Z COMMIT: 83a7113e8 feat(approvals): filter by type and approve many requests at once → review+design dispatched
- 2026-10-05 PLAN B step 2 fix found while the reviewers ran: ages and the banner used the UTC date (new Date().toISOString().slice(0,10)), so an approver at UTC+8 between midnight and 8 am saw every wait one day short (verified: a request really 1 day old read 1 vs 2 by the site calendar). Now siteToday(new Date(), siteTimeZone()) (new, tested: KL 23:30Z -> next day; bad zone falls back). 49 node tests green; the page test fails if the UTC date comes back.
- 2026-10-05T08:05:46Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-05T08:05:50Z COMMIT: 6e0415333 fix(approvals): a wait read one day short for an approver before 8 am in Malaysia → review+design dispatched
- 2026-10-05 PLAN B reviews of the Approvals page (frappe-reviewer: 1 CRITICAL; design: FIX_WARNINGS, 5 warnings). CRITICAL FIXED (server): check_many handed back the server's FRESH `modified`, so a request the employee edited after the approver's list loaded would go through for dates the approver never saw (the check only covered check -> approve). Now it compares the revision the approver SAW and refuses a mismatch as "changed"; ready rows keep the approver's revision. EVIDENCE: 21 python tests (red first: 2 failed), 2 breaks each fail a test; real fresh.local probe: a leave edited after the list loaded is refused "changed" at the check AND by decide() if sent anyway; the other two behave as before.
OPEN from the reviews (page): ticks outlive the filter and Other-teams rows can be ticked unseen (Select all runs over visibleRows incl. Other teams) -> scope pickable/itemsFor to Yours + the filter and clear ticks on a filter change; sticky bar vs tab bar + safe area; age badge contrast (3 of 4 below 4.5:1); in-sheet failure state with retry; "nothing tickable" hint for Check-ins; dismiss while working. Desktop Table view (searchRows/sortRows done + tested, UI not built).
- 2026-10-05T08:08:29Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T08:08:29Z EVIDENCE: 3 works — blast radius green: 13 dependent(s), 10 extra test file(s) ⟂c895fe9eab8e
- 2026-10-05T08:08:34Z COMMIT: b5dd26acb fix(approvals): bulk approve could approve dates the approver never saw → review dispatched
- 2026-10-05T08:11:32Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-05T08:11:36Z COMMIT: 2c5d0ce57 fix(approvals): Select all ticked requests nobody could see → review+design dispatched
- 2026-10-05 PLAN B page fixes after the reviews (frappe-reviewer + design): Select all / Approve now cover only what the approver can SEE ticked (Yours, not check-ins) and follow the filter (keepVisible drops ticks no longer shown; itemsFor runs over visibleRows); a filter with nothing tickable says "These are approved one by one"; a failed check/approve stays IN the sheet with "Nothing was approved. Your ticks are kept." + Try again (no vanishing toast); closing the sheet while the server is approving is ignored; age badge tint 14% -> 8% (3 of 4 cases were under 4.5:1); "Select all in this filter" -> "Select all shown". EVIDENCE: 63 node tests green; 4 page breaks each fail a test. NOT YET DONE: sticky bar vs the floating tab bar + safe-area (needs a look in the real app), the desktop Table view UI (searchRows/sortRows exist, tested), in-app dark theme and 320px check.
- 2026-10-05 PLAN B DSN-2 (design pass 1): the sticky "Approve N" bar used bottom:0, which sticks to the scrollport edge the floating tab bar overlays, with no safe area. Now bottom: max(var(--padding-bottom,0px), env(safe-area-inset-bottom,0px)) (ion-content's own tab-bar reservation, theme/glass-components.css:66-72) and the page gets 88px of padding while the bar shows. Tests pin both (red first). NOT verified by eye on a device/in the real app (Approvals is a tab child at router/index.js:190, so the tab bar is present); iOS safe area + the 320px check still need a look.
- 2026-10-05T08:13:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T08:13:53Z COMMIT: 49b360546 fix(approvals): the Approve bar sat under the tab bar → review+design dispatched
- 2026-10-05 PLAN B review round 3 (frappe-reviewer: no Critical; design pass 2: FIX_WARNINGS). FIXED: (1) the sheet cannot be closed under a working request - the refusal now lives in GModal (new `dismissible` prop: Close button + scrim + Ionic gestures/Escape via can-dismiss) because ignoring did-dismiss in the handler leaves is-open true after Ionic closed the overlay; (2) a failed APPROVE no longer says "Nothing was approved" (decide_many may have got some through): its own phase "We could not confirm what was approved. The list is reloading." and the reload is wrapped; (3) age badge: measured 8% tint = 4.37/4.20 on --g-bg, plain ink = 4.86/4.83 -> no tint; (4) dead `retry` field removed; (5) the sticky bar sits above the tab-bar reservation + safe area. EVIDENCE: 170 node tests green incl. every glass test; 4 breaks (modal closable, Ionic gesture, Close/scrim, wrong failure text) each fail a test; vite build compiles. STILL OPEN: i18n (__(chip.label) is dynamic - add literals), a one-line "N approved one by one" for hidden rows in select mode, desktop Table view UI, 320px/dark/iOS look, the bar's margin/radius on desktop (design suggested).
- 2026-10-05T08:16:01Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-05T08:16:06Z COMMIT: 987a14819 fix(approvals): the Approve sheet could be closed under a working request → review+design dispatched
- 2026-10-05 REVIEW 987a14819 final (frappe-reviewer): no Critical. WARNING for the owner: the Approve sheet cannot be closed while "working", with no timeout, so a request that never returns leaves no way out. Recommended: after ~20 s allow close + "Taking long?" hint. Not built.
- 2026-10-05T08:35:17Z PUSH: nz-glass @ af05c1670
- 2026-10-05T09:03:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-05T09:03:59Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-05T09:04:06Z COMMIT: 473d9cf11 fix(auth): the next person on a shared phone kept getting the last person's pushes → review+security+design dispatched
- 2026-10-05 AUTHZ HUNT (3 hunters + my own probes; reports in /tmp/hunt/*.md). OWNER RULINGS TODAY: (1) H1 System Manager must NOT approve/reject check-ins outside the area: "HR only"; (2) H2 leave reason: "approvers yes, others no". FIXED H1: _is_routed_approver now uses HR_SEE_ALL_ROLES (not System Manager), and validate_inherited_checkout no longer keeps its own System-Manager list (uses may_decide). PROVEN on fresh.local before/after: an admin-only login was ADMITTED by remote_checkin._ensure_approver for another company's check-in, now REFUSED; an admin who also holds HR Manager keeps the right. Tests: 13 + 4 green (red first). AU-1 (push token after logout) fixed in 473d9cf11.
STILL OPEN from the hunt: H2 leave reason to managers who are not approvers (ruled, not built; get_leave_applications api/__init__.py:1116 + matrix wording); H3 finalize on an undecided request: NOT REPRODUCED (own employee is refused at the read gate; named approver is refused by each controller's on_submit status check, all 7 doctypes checked) - downgraded to a hardening note; M1 report_half_transitioned selects `company` from Compensatory Leave Request (no such column) -> 500 for HR; M3 appraisal raw identity (Desk only); M5 upload_base64_file attached_to_field client-supplied; L4 get_leave_approver raw compare; AU-2..5 session UX; M1/M2 flows: rejection REASON missing from the employee's notification, no approver told when the approver field is blank; stale tests fixed below.
- 2026-10-05T09:15:42Z EVIDENCE: 6 behaves — family hunt: class=a decision gate that names System Manager next to the HR roles, so an admin-only lo; 5 call site(s) given verdicts, 2 same-root ⟂101f7acbc7fc
- 2026-10-05T09:17:17Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:17:17Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 14 extra test file(s) ⟂37afa90f943c
- 2026-10-05T09:17:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:17:34Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 14 extra test file(s) ⟂37afa90f943c
- 2026-10-05T09:17:48Z EVIDENCE: 6 behaves — family hunt: class=a decision gate that names System Manager next to the HR roles, so an admin-only lo; 6 call site(s) given verdicts, 1 same-root ⟂419e55a601b8
- 2026-10-05T09:18:33Z COMMIT: 9623902c1 test: two OT tests went stale and no longer tested what they say → review dispatched
- 2026-10-05T09:18:55Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:18:55Z EVIDENCE: 3 works — blast radius green: 17 dependent(s), 14 extra test file(s) ⟂37afa90f943c
- 2026-10-05T09:18:59Z EVIDENCE: 6 behaves — family hunt: class=a decision gate that names System Manager next to the HR roles, so an admin-only lo; 6 call site(s) given verdicts, 1 same-root ⟂419e55a601b8
- 2026-10-05T09:19:04Z COMMIT: 3faf00848 fix(approvals): a System Manager could decide any company's check-in outside the area → review dispatched
- 2026-10-05 H2 (leave reason) BUILT per the owner ruling "approvers yes, others no": new approval.may_read_leave_reason(doc, user) = the employee, an approver on the request's LINE (get_designated_approvers: the named approver, the reports_to manager, and each level up to HR Settings' approval_levels, default 2), or HR inside its company fence; NOT a System Manager alone, NOT someone past the levels. Asked by BOTH doors: get_leave_applications (reason blanked) and the Approvals page row. NOTE for the owner: the direct reports_to manager IS on the line by the 21 and 29 Sep rulings, so he still reads the reason (the 13 Sep audit said "manager never"; the access matrix now says what the code does). PROVEN on fresh.local (probe_h2e): employee/named approver/level-2 approver read it; a person past level 2 and a stranger are refused (the list endpoint itself refuses them). 9 + 31 tests green (red first), ACCESS-MATRIX updated.
- 2026-10-05T09:24:48Z EVIDENCE: 6 behaves — family hunt: class=a private field sent to everyone who can open the record. The leave REASON (Leave A; 8 call site(s) given verdicts, 3 same-root ⟂e237a6a149e5
- 2026-10-05T09:25:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 8 file(s) ⟂f8ce4dca95f0
- 2026-10-05T09:25:02Z EVIDENCE: 3 works — blast radius green: 15 dependent(s), 13 extra test file(s) ⟂08f9e39b63c4
- 2026-10-05T09:25:04Z EVIDENCE: 6 behaves — family hunt: class=a private field sent to everyone who can open the record. The leave REASON (Leave A; 8 call site(s) given verdicts, 3 same-root ⟂e237a6a149e5
- 2026-10-05T09:25:05Z COMMIT: a5fc9433f fix(requests): a person past the approval line could read a leave reason → review dispatched
- 2026-10-05T09:26:04Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-05T09:26:04Z EVIDENCE: 3 works — blast radius green: 14 dependent(s), 11 extra test file(s) ⟂e3a82f02d393
- 2026-10-05T09:26:05Z COMMIT: c69fd2d4e fix(approvals): HR's decided-but-still-draft report failed for everybody → review dispatched
- 2026-10-05 FLOWS M1 (rejection reason) + M1 (half-transitioned report) FIXED. (a) c69fd2d4e: report_half_transitioned selected `company` from every approvable doctype; Compensatory Leave Request has none -> HR's report threw for everybody; each type now asked only for columns it has (proven on fresh.local: before THREW, after lists all 7 types). (b) the employee's "Rejected" notice never said WHY (the approver is forced to write a reason, kept only as a Comment): decide() now sets doc.flags.rejection_reason BEFORE doc.submit() (the notice is built inside on_submit) and notify_approval_status appends it, HTML-escaped, for a Rejected decision only. PROVEN end to end on fresh.local through the real decide(): message ends "Reason: No cover that week &lt;b&gt;sorry&lt;/b&gt; &amp; thanks"; the Comment for the sheet is still recorded. Tests red first; 3 breaks each fail a test. Reviewer of a5fc9433f (leave reason): no Critical; WARNING N+1 per row in get_leave_applications (1.5 queries/row, fine at 10-50 rows, cache per employee if pages grow); SUGGESTION: a level-2 approver reads the reason in the list but frappe.client.get refuses them (sheet vs list disagree, not a leak).
STILL OPEN from the hunt (not built): M2 no approver is told when the approver field is blank on Leave/Expense/Shift; M3 appraisal raw identity (Desk only); M5 upload_base64_file attached_to_field; L4 get_leave_approver raw compare; AU-2..5 session UX; the Approve-sheet timeout; per-row N+1 in get_leave_applications; level-2 approver sheet vs list.
- 2026-10-05T09:29:20Z EVIDENCE: 6 behaves — family hunt: class=a decision's WHY recorded in one place and never carried to the one it concerns. de; 36 call site(s) given verdicts, 2 same-root ⟂5d6829671a45
- 2026-10-05T09:29:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-05T09:29:31Z EVIDENCE: 3 works — blast radius green: 22 dependent(s), 18 extra test file(s) ⟂cebb1b0e4801
- 2026-10-05T09:29:32Z EVIDENCE: 6 behaves — family hunt: class=a decision's WHY recorded in one place and never carried to the one it concerns. de; 36 call site(s) given verdicts, 2 same-root ⟂5d6829671a45
- 2026-10-05T09:29:33Z COMMIT: f5941bed4 fix(requests): an employee was told Rejected and never why → review dispatched
- 2026-10-05T09:34:37Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-05T09:34:37Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 7 extra test file(s) ⟂07285428dc7c
- 2026-10-05T09:34:40Z COMMIT: ad0579c73 fix(requests): a request with no named approver reached nobody → review dispatched
- 2026-10-05T09:36:53Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-10-05T09:38:37Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-05T09:38:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T09:39:10Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T09:39:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T09:39:53Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T09:40:11Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T09:40:14Z COMMIT: ad0579c73 fix(requests): a request with no named approver reached nobody → review dispatched
- 2026-10-05T09:40:27Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-05T09:40:32Z COMMIT: 1ad6e6c7d fix(notifications): a rejected request showed no reason in the feed → review+design dispatched
- 2026-10-05T09:43:03Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-05T09:43:03Z EVIDENCE: 3 works — blast radius green: 8 dependent(s), 7 extra test file(s) ⟂07285428dc7c
- 2026-10-05T09:43:07Z COMMIT: 261f60b9e fix(notifications): a rejection reason reached the phone with &amp; in it → review dispatched

## 5 Oct 2026 (late): hunt continues, nothing pushed
EVIDENCE: correct half/full-day leave traced on fresh.local (request -> approve -> cancel -> amend -> attendance rebuilt); probes /tmp/probe_hd1.py, /tmp/probe_hd2.py; reviews of 1ad6e6c7d and 261f60b9e: no Critical/Warning.
DEAD END: none new. Release gate keeps asking to push; owner said push only on his word and keep the safety tag local.
NEXT: (1) route announcements._push_to_users through push_body (same &amp; defect); (2) read /tmp/wording-inventory.md (scout) and fix PWA-vs-Desk wording mismatches; (3) trace amend/rebuild for OT, Attendance Request, Expense Claim; (4) AU-2 signed-out notice, AU-3 only Guest 403 = session lost (verified: expired session gives PermissionError 403 via is_whitelisted), AU-5, N+1 in get_leave_applications; (5) wait for "push".
- 2026-10-05T09:52:51Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-10-05T09:52:51Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-05T09:52:54Z COMMIT: ff899b5a4 fix(team): a day HR marked half showed the boss a bare "Present" → review+design dispatched
- 2026-10-05T09:54:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-05T09:54:50Z COMMIT: 9d6a5e062 fix(team): "Half day" was the first thing cut off on a phone → review+design dispatched
- 2026-10-05T09:55:49Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T09:55:49Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-05T09:55:51Z COMMIT: 8cdbedec5 fix(team): an old draft attendance row could hide a day HR marked half → review dispatched
- 2026-10-05T09:59:53Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T09:59:53Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 4 extra test file(s) ⟂5c6fe2548ee6
- 2026-10-05T09:59:55Z COMMIT: a5c28c876 fix(ot): the refusal named overtime to nine decimals → review dispatched
- 2026-10-05T10:00:25Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T10:00:28Z COMMIT: bc350a0a6 fix(ot): the claim box opened on a nine-decimal number → review+design dispatched
- 2026-10-05T10:01:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-05T10:01:51Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 4 extra test file(s) ⟂5c6fe2548ee6
- 2026-10-05T10:01:53Z COMMIT: e806aab52 fix(ot): a refused claim could read equal to its cap → review dispatched
- 2026-10-05T10:04:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T10:04:42Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
- 2026-10-05T10:04:44Z COMMIT: 0e08bffd5 fix(ot): a stored minute read as two minutes in the refusal → review+design+cross-app dispatched
- 2026-10-05T10:05:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-10-05T10:05:39Z COMMIT: 0d1bfd039 fix(desk): one word per state in Desk, the same as Nadi → review+design dispatched
- 2026-10-05T10:08:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-05T10:08:00Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
- 2026-10-05T10:08:03Z COMMIT: 1070014b4 chore(ot): name the one limit of the minute words → review dispatched
EVIDENCE: announcements push NOT affected by the "&amp;" class (checked 5 Oct 2026): HR Announcement.summary is Small Text, controller strips tags on save (hr_announcement.py:55), stored as typed text, not escaped HTML. Routing it through push_body would wrongly decode a typed "&amp;". Left alone.
NEXT: (1) read the review of 1070014b4; (2) AU-2 signed-out notice, AU-3 only Guest 403 counts as lost session (probe: expired session = PermissionError 403 from is_whitelisted, so 403 alone cannot be dropped), AU-5; (3) trace amend/rebuild for OT, Attendance Request, Expense Claim; (4) Desk wording: Expense Claim + Remote Checkin (ticket, needs Nabil's word); (5) OD2 (30-min banding of typed claims) needs Nabil's ruling; (6) wait for "push" (17+ commits local).
- 2026-10-05T10:18:32Z PUSH: nz-glass @ 1070014b4
- 2026-10-05T10:20:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T10:20:42Z COMMIT: 1c63f546b fix(roster): the shift picker showed only shifts named like the chosen one → review+design dispatched
- 2026-10-05T10:23:18Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T10:23:22Z COMMIT: 3a860c31e fix(roster): the shift picker lost the chosen person's name and its tick → review+design dispatched

## 5 Oct 2026 (end of session): pushed 18, roster picker fix local
EVIDENCE: pushed af05c1670..1070014b4 to origin/nz-glass on Nabil's "push" (branch only, safety tag stays local). Roster picker: 1c63f546b + 3a860c31e local; shown 2 of 25 shifts before, 25 of 25 after (search_link probe on fresh.local); reviews of 1c63f546b gave two real warnings (bare id label, no tick), fixed in 3a860c31e.
OWNER RULINGS (5 Oct): OT typed claims banded to 30 min (YES, NOT BUILT YET: validate_claimed_hours should round_ot_pay_hours the claim for Overtime Pay only; Replacement Leave unchanged); Desk wording for Expense Claim and Remote Checkin Request YES (NOT BUILT: ticket-desk-wording-expense-remote.md).
DEAD END: the pre-commit hook bundles co-modified tracked files into the next commit (hit twice: 0e08bffd5, a5c28c876); stage the pair and commit in separate commands; the gate checks before the command runs.
LEARNING(gate): a stub test that mocks frappe.bold/_ passes without reading the message -> assert on caught.exception text with bold/_ patched (done in test_ot_storage_precision.py).
NEXT: (1) read the two reviews of 3a860c31e, fix real findings, then push branch only (Nabil said check before push); (2) build the OT 30-min banding of typed claims (ruled YES); (3) Desk wording for Expense Claim + Remote Checkin (ruled YES); (4) AU-2 signed-out notice on Submit, AU-5 stale cached page; (5) trace amend/rebuild for OT, Attendance Request, Expense Claim; (6) after deploy: Leave list in Desk must say Waiting (else a live Workflow overrides).
- 2026-10-05T10:25:28Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T10:25:34Z COMMIT: d94faafcd fix(roster): the picker's closed box went blank while typing a search → review+design dispatched
- 2026-10-05T10:27:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T10:27:41Z COMMIT: 72f38eb43 fix(roster): the picker's closed box could still go blank while typing → review+design dispatched
- 2026-10-05T10:29:30Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-10-05T10:29:30Z EVIDENCE: 3 works — blast radius green: 9 dependent(s), 4 extra test file(s) ⟂5c6fe2548ee6
- 2026-10-05T10:29:32Z COMMIT: 66f0ed539 feat(ot): a typed Overtime Pay claim is cut down to the half hour → review dispatched
- 2026-10-05T10:30:21Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T10:30:24Z COMMIT: b4ba0595a fix(roster): the picker's own box was not disabled and had no name → review+design dispatched
- 2026-10-05T10:32:51Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T10:32:51Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 2 extra test file(s) ⟂a5801cfef452
- 2026-10-05T10:32:52Z COMMIT: b9ca0e8dd fix(ot): the half-hour rule could cut a claim an approver had already read → review dispatched
- 2026-10-05T10:34:12Z PUSH: nz-glass @ b9ca0e8dd
- 2026-10-05T11:11:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-05T11:11:13Z COMMIT: 112adc0af feat(ot): the claim form says overtime is paid in half hours → review+design dispatched
- 2026-10-05T11:14:33Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T11:14:36Z COMMIT: eb32c90c8 chore(ot): cut open Overtime Pay claims to the half hour on deploy → review+design dispatched
- 2026-10-05T11:17:00Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-05T11:17:02Z COMMIT: 89502794a fix(ot): the cleanup patch kept the old claim figure nowhere readable → review dispatched
- 2026-10-05T11:19:22Z PUSH: nz-glass @ 89502794a
- 2026-10-05T11:26:14Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T11:26:16Z COMMIT: 2110f2ec7 fix(desk): a remote check-in request says Waiting, like Nadi → review+design dispatched
- 2026-10-05T11:29:12Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 7 file(s) ⟂85be7f79c548
- 2026-10-05T11:29:14Z COMMIT: 3f761024f fix(desk): an expense claim says Waiting / Approved · unpaid / Paid, like Nadi → review+design dispatched
- 2026-10-05T11:30:32Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-05T11:30:35Z COMMIT: 6976d80c0 fix(desk): the "Approved · unpaid" pill listed too few claims when clicked → review+design dispatched
- 2026-10-05T11:41:04Z COMMIT: 299b1c267 docs(plan): stabilise Nadi and keep Desk in good hands → review dispatched
- 2026-10-06T01:35:51Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T01:35:54Z COMMIT: 3a54590cd fix(checkin): the Today status line stayed stale after a punch → review+design dispatched
- 2026-10-06T01:37:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T01:37:52Z COMMIT: 18026f349 fix(checkin): a burst of other people's punches would reload four reads each → review+design dispatched
- 2026-10-06T01:49:31Z COMMIT: 6253bdc45 fix(pwa): pull-down and load-more-on-scroll never ran on the real app → review+design dispatched
- 2026-10-06T01:50:30Z COMMIT: bb0d5a450 test(e2e): a real pull-down and a real scroll are checked on the running app → review+design dispatched
- 2026-10-06T02:10:09Z COMMIT: 9f56f8a5d test(e2e): the pull gate pulled 360 px and failed on its own second pull → review+design dispatched

## 6 Oct 2026: real-browser work, check-in and pull-down fixed
EVIDENCE: drove the running app on fresh.local in a real browser (Playwright, iPhone 13, real touch events). (1) check-in: after a punch the button changed but the Today status line stayed stale until reload; fixed (3a54590cd + debounce 18026f349), verified live: line changes within 600 ms. (2) pull-down: the element fires "ion-refresh"/"ion-scroll" (@ionic/vue renames events to kebab-case), the app listened for camelCase, so a real pull made 0 requests on Home/Requests/Approvals/Announcements and load-more never ran; fixed 6253bdc45. The 28 Sep fix was pinned by source-reading tests that stayed green. Gates: e2e/pull-refresh.spec.js (4/4 red with the old listener, 3/3 green runs with the fix) + e2e/list-scroll.spec.js.
DEAD END: the first pull spec dragged 360 px and logged two refreshes (Ionic starts at 120 px, the rest of the drag was a second pull): a test artefact, not an app bug; probes with touch/mouse/fast release each ran the handler once.
LEARNING(gate): a fix for "does nothing on the real app" is proven only by a test that runs the real app; source-text tests cannot see an event-name mismatch. The commit gate runs *.spec.js with bun, which cannot run Playwright: use a `test(e2e):` commit, which the gate skips.
OPEN: 7 untracked probe scripts frontend/e2e/live-*.mjs (delete or fold into tests); countWords.test.js and notifications-reason.test.js untracked from earlier; no pull-down on Notifications/Team/Roster/two dashboards/Issues/Helpdesk (plan Stage 1.3); AU-2 signed-out message; stale cached page AU-5; update-after-deploy only while hidden; ticket realtime-fanout (useListUpdate has no debounce/filter for any caller); two Desk gaps from the plan.
NEXT: push the 9 reviewed commits (branch only; Nabil said push when all done), then Stage 1 of docs/glass/plan/2026-10-05-stabilise-nadi-plan.md: signed-out message, pull-down on the screens that lack it (now a real gate exists), counts, required expected_modified.
- 2026-10-06T02:10:59Z COMMIT: d20fc621d docs(plan): note the list second-page gap and the 6 Oct real-browser findings → review dispatched
- 2026-10-06T03:02:37Z PLAN: approved ae107bc4bd38 — # Release 2.0.0-alpha.35 "Steady Nadi" (6 Oct 2026)
- 2026-10-06T03:04:54Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T03:04:57Z COMMIT: 55b190300 fix(requests): the request chips never counted compensatory leave → review dispatched
- 2026-10-06T03:05:19Z COMMIT: f96f1f53e test(placeholders): the empty-queue test failed on quote style, not on the row → review+design dispatched
- 2026-10-06T03:08:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-06T03:08:11Z COMMIT: ef5509251 fix(requests): the chips would count compensatory leave the list never shows → review dispatched
- 2026-10-06T03:09:22Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T03:09:23Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-06T03:09:28Z COMMIT: 4ab2dd0a3 fix(pwa): an app kept open never looked for a new build after a deploy → review+design dispatched
- 2026-10-06T03:09:58Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T03:09:58Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-06T03:10:08Z COMMIT: 17de8474d fix(pwa): an app kept open never looked for a new build after a deploy → review+design dispatched
- 2026-10-06T03:10:54Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T03:10:54Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 0 extra test file(s) ⟂2065c46f7f10
- 2026-10-06T03:10:57Z COMMIT: 7036458ff fix(pwa): an app kept open never looked for a new build after a deploy → review+design dispatched
- 2026-10-06T03:17:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 9 file(s) ⟂0819c392f5b2
- 2026-10-06T03:17:42Z EVIDENCE: 3 works — blast radius green: 15 dependent(s), 12 extra test file(s) ⟂84fa3520acad
- 2026-10-06T03:17:44Z COMMIT: 17136b06d fix(approvals): a decision without the revision the approver read skipped the check → review dispatched
- 2026-10-06T03:18:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-06T03:18:21Z EVIDENCE: 3 works — blast radius green: 15 dependent(s), 12 extra test file(s) ⟂84fa3520acad
- 2026-10-06T03:18:24Z COMMIT: 37b666465 perf(leave): the leave list read the database once per row for the reason check → review dispatched
- 2026-10-06T03:21:27Z COMPACT: context compacted — read the last NEXT above before continuing
- 2026-10-06T03:26:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-06T03:26:50Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 10 extra test file(s) ⟂26261ccd9d8d
- 2026-10-06T03:32:37Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-10-06T03:32:41Z COMMIT: 3e6df44b1 fix(pwa): pulling down did nothing on seven screens → review+design dispatched
- 2026-10-06T03:40:02Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-06T03:40:09Z COMMIT: 873ceee08 test(helpdesk): the hub test could not build the page after pull-down landed → review+design dispatched
- 2026-10-06T04:24:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T04:25:05Z COMMIT: e089c3d3d fix(issues): HR pulling down on the issue board did nothing → review+design dispatched
- 2026-10-06T04:25:17Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T04:25:20Z COMMIT: 397c34910 fix(attendance): the calendar pull closed before the month had loaded → review+design dispatched
- 2026-10-06T04:25:33Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-06T04:25:33Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 10 extra test file(s) ⟂26261ccd9d8d
- 2026-10-06T04:25:38Z COMMIT: 666d6007b fix(session): a failed Log out could hide a later "you were signed out" → review+security+design dispatched
- 2026-10-06T04:25:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T04:25:52Z COMMIT: c6d8abb4d fix(login): an expired session left the last page copy on the phone → review+security+design dispatched
- 2026-10-06T04:26:17Z COMMIT: ee75de979 test(e2e): the pull-refresh gate covers the seven screens that lacked it → review+design dispatched
- 2026-10-06T04:27:05Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-10-06T04:27:08Z COMMIT: 9cc7d3563 test(checkin): the no-selfie guard test read the indent, not the guard → review dispatched
- 2026-10-06T04:30:07Z COMMIT: 1ef5b3271 docs(audit): the Shift Supervisor Desk probe has no supervisor to run as → review dispatched
- 2026-10-06T04:32:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T04:32:42Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-10-06T04:32:50Z COMMIT: d21f3dad9 perf(approvals): the approvals list asked the leave-reason rule once per row → review dispatched
