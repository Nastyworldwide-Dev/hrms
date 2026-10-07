2026-09-07T05:12Z NEXT: audit report at docs/glass/nadi-audit-2026-09-07.md (uncommitted); fix order D1 icon roles, D2 report timestamps+patch, F1 e2e URLs+CSRF header
2026-09-07T07:20Z COMMIT: ec2224979 fix late-checkout bound; 7c9ed90d6 feat re-mark attendance on approval; 776ee69ec audit doc; pushed 108d7158f
2026-09-07T07:20Z NEXT: Nabil deploys (bench migrate runs); then audit fix plan row 1 (desktop_icon roles) + row 2 (payroll report timestamps + patch)
2026-09-07T07:25Z COMMIT: 778774f58 same-punch window; 81f68b879 double toast; pushed
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
- 2026-10-06T04:34:26Z COMMIT: 5e0c6fdd0 chore(release): 2.0.0-alpha.36 Loose Ends → review+deps dispatched

- 2026-10-06 alpha.36 "Loose Ends" released: tag v2.0.0-alpha.36. A1-A4, O1, D1 (pipeline-health reads wrapped upgrade:), D2 tickets, G1 (pre-commit-test leaves e2e specs to Playwright; humanless-pipeline 6777dcb, local), G2 (.no-release-gate).
DEAD END: V1 supervisor probe: fresh.local has no Shift Supervisor with reports; setting a test password was refused.
NEXT: owner deploys; seed a supervisor on fresh.local (owner call) then run /tmp/slices/alpha36-V1.md; humanless-pipeline commits 6777dcb + 0639d1a are local, push on owner word; bench (evals/ab.sh) not run.
- 2026-10-06T04:35:03Z PUSH: nz-glass @ 405c1997d
- 2026-10-06T04:35:04Z COMMIT: 405c1997d docs(handoff): alpha.36 released → review dispatched
- 2026-10-06T04:45:42Z COMMIT: 405c1997d docs(handoff): alpha.36 released → review dispatched
- 2026-10-06T04:49:10Z COMMIT: 405c1997d docs(handoff): alpha.36 released → review dispatched
- 2026-10-06T04:52:07Z COMMIT: 679cc0255 docs(audit): a Shift Supervisor on Desk sees their team and no one else → review dispatched
- 2026-10-06T04:57:49Z COMMIT: e3474242c docs(audit): owner rulings on supervisor access; remote check-ins tested → review dispatched
- 2026-10-06T05:26:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T05:26:40Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-06T05:26:43Z COMMIT: 929945a60 fix(pwa): a page you may not open said "Could not load, try again" → review+security+design dispatched
- 2026-10-06T05:26:54Z EVIDENCE: 2 correct — mapped tests green (bun ) for 17 file(s) ⟂da5fdd6c5fcd
- 2026-10-06T05:26:56Z COMMIT: 3e3a09306 fix(pwa): a long name or reason wrapped rows onto three lines on a phone → review+design dispatched
- 2026-10-06T05:28:25Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T05:28:28Z COMMIT: 5ddbc5e01 fix(a11y): a screen reader opening any sheet heard "dialog" and no name → review+design dispatched
- 2026-10-06T05:29:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T05:29:09Z COMMIT: c946b1ce7 fix(a11y): the must-read notice was an unnamed dialog too → review+design dispatched
- 2026-10-06T05:29:52Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T05:29:54Z COMMIT: adaa441b1 fix(pwa): a long name could cut off how many requests are waiting → review+design dispatched
- 2026-10-06T05:31:08Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T05:31:11Z COMMIT: 1049cbd54 fix(a11y): every toast had an unnamed 20 px close button → review+design dispatched
- 2026-10-06T05:34:24Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-06T05:34:27Z COMMIT: 0fc29cea0 fix(a11y): a sheet was announced as two dialogs, and Close was English only → review+design dispatched
- 2026-10-06T05:42:58Z EVIDENCE: 2 correct — mapped tests green (bun ) for 13 file(s) ⟂884c4344e835
- 2026-10-06T05:42:58Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 13 extra test file(s) ⟂2d3ffee99479
- 2026-10-06T05:43:02Z COMMIT: 594cc6b6b refactor(session): one function decides that the session ended → review+security+design dispatched
- 2026-10-06T05:45:32Z COMMIT: 9def8161d chore(a11y): the known-problems list was out of date; it is now empty → review dispatched
- 2026-10-06T05:48:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T05:48:05Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 10 extra test file(s) ⟂26261ccd9d8d
- 2026-10-06T05:48:08Z COMMIT: f42188553 fix(session): a 403 that is not an expiry could reload the page forever → review+security+design dispatched
- 2026-10-06T05:49:39Z COMMIT: 0db6c24c6 chore(release): 2.0.0-alpha.37 Clear Screens → review+deps dispatched

- 2026-10-06 alpha.37 "Clear Screens" released: tag v2.0.0-alpha.37. B2 no-access sentence, B3 one-line names (+summary rows wrap), B1 sheet/notice/toast names (16-item a11y baseline was stale: 0 serious on 76), R1 sessionEnded owner + reload-loop guard, V1 supervisor Desk audit + owner rulings, P1 lint hook re-linked to humanless-pipeline (was /opt/keel bare git add -u), T1 test HR + supervisor on fresh.local.
DEAD END: 25 other ~/.claude/hooks still link /opt/keel (older versions) - owner call, one gate at a time.
NEXT: owner deploys; alpha.38 = second toast after no-access, 4 parts blank on failed load (RequestTimeline, ExpensesTable, ExpenseTaxesTable, MustReadNotice); humanless-pipeline commits local (6777dcb, 0639d1a, c6ac5e7).
- 2026-10-06T05:49:58Z PUSH: nz-glass @ b04e69ab6
- 2026-10-06T05:49:58Z COMMIT: b04e69ab6 docs(handoff): alpha.37 released → review dispatched
- 2026-10-06T06:26:20Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T06:26:24Z COMMIT: ecf979a03 feat(approvals): a request does not wait on an approver who is on leave → review dispatched
- 2026-10-06T06:28:34Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T06:28:36Z COMMIT: 68b8306f9 fix(approvals): someone could get two reminders on the same morning → review dispatched
- 2026-10-06T06:55:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-06T06:55:06Z EVIDENCE: 3 works — blast radius green: 5 dependent(s), 3 extra test file(s) ⟂17919a97fd02
- 2026-10-06T06:55:09Z COMMIT: 2dca91f50 feat(requests): cancelling an approved request tells its approver and HR → review+cross-app dispatched
- 2026-10-06T06:58:27Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T06:58:27Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-06T06:58:31Z COMMIT: 1b6d48c1c fix(approvals): a long leave with one half day was not read as away → review dispatched
- 2026-10-06T07:00:09Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T07:00:09Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-06T07:00:13Z COMMIT: f5ed29ab4 fix(expense): the same expense could be claimed and paid twice → review dispatched
- 2026-10-06T07:02:21Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T07:02:21Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-06T07:02:26Z COMMIT: ff7e6c09b fix(expense): a copy filed later made the original claim unapprovable → review dispatched
- 2026-10-06T07:05:42Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-06T07:05:42Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-06T07:05:44Z COMMIT: 6fc26b344 fix(expense): an old draft edited to copy a newer claim slipped past the check → review dispatched
- 2026-10-06T07:11:16Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T07:11:16Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-06T07:11:19Z COMMIT: f370bb56d fix(expense): adding a receipt to an original claim was refused for its old line → review dispatched
- 2026-10-06T07:59:34Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-06T07:59:40Z COMMIT: 3b7b8bc1f fix(sop): HR editing an SOP in Nadi saw raw code and could not format it → review+design dispatched
- 2026-10-06T08:01:15Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 11 file(s) ⟂754ac19061fd
- 2026-10-06T08:01:15Z EVIDENCE: 3 works — blast radius green: 6 dependent(s), 2 extra test file(s) ⟂cf4a11809724
- 2026-10-06T08:01:19Z COMMIT: df96cb48c feat(expense): Nadi shows the "you already claimed this" warning too → review+security+design+cross-app dispatched
- 2026-10-06T08:03:16Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T08:03:25Z COMMIT: 4e1563923 fix(sop): a picture HR inserted in an SOP showed empty to staff → review+design dispatched
- 2026-10-06T08:06:46Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-06T08:06:46Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-06T08:06:48Z COMMIT: 8c139e61a fix(expense): the warning could name claims the reader may not open → review+security+cross-app dispatched
- 2026-10-06T08:09:03Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-06T08:09:03Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-06T08:09:08Z COMMIT: 5ea4435a0 fix(expense): the Desk warning could name claims the saver may not open → review dispatched
- 2026-10-06T08:14:40Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T08:14:40Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-10-06T08:14:44Z COMMIT: daac5cf1b fix(pwa): a form sent while offline said "Failed to fetch" → review+design dispatched
- 2026-10-06T08:20:05Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-06T08:20:05Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-10-06T08:20:09Z COMMIT: 379d9adea fix(pwa): the offline message was wrong when only the server was down → review+design dispatched
- 2026-10-06T08:20:25Z COMMIT: b7386baa7 docs(tickets): loudRequest.js decides, words and tracks failures in one place → review dispatched
- 2026-10-06T08:26:02Z COMMIT: 8d0f8f66f docs(audit): approver roles see no report rows outside their scope → review dispatched
- 2026-10-06T08:46:46Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
- 2026-10-06T08:46:46Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-10-06T08:46:49Z COMMIT: b29d23890 fix(pwa): a record you may not open still offered "try again" → review+design dispatched
- 2026-10-06T08:46:59Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-06T08:47:03Z COMMIT: 7ad51473d fix(pwa): four parts of a screen went blank when they failed to load → review+design dispatched
- 2026-10-06T08:47:15Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T08:47:15Z EVIDENCE: 3 works — blast radius green: 25 dependent(s), 10 extra test file(s) ⟂26261ccd9d8d
- 2026-10-06T08:47:17Z COMMIT: 007287e73 fix(session): another person signing in left the old page up for a moment → review+design dispatched
- 2026-10-06T08:47:29Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-06T08:47:29Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-06T08:47:38Z COMMIT: 524087f4e test(pwa): two audits and the overtime form tests went red unseen on 5 Oct → review+design dispatched
- 2026-10-06T08:56:36Z EVIDENCE: 2 correct — mapped tests green (bun ) for 9 file(s) ⟂0e91782f6c7d
- 2026-10-06T08:56:36Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-10-06T08:56:39Z COMMIT: 9ced39c7c fix(pwa): a must-read could be confirmed unseen; some refusals said nothing → review+design dispatched
- 2026-10-06T08:59:06Z EVIDENCE: 2 correct — mapped tests green (bun ) for 3 file(s) ⟂788cca13b6a1
- 2026-10-06T08:59:06Z EVIDENCE: 3 works — blast radius green: 4 dependent(s), 1 extra test file(s) ⟂b7fff5e7f6e0
- 2026-10-06T08:59:09Z COMMIT: 0f4e8595f fix(pwa): a refusal on an earlier page could hide the one in view → review+design dispatched
- 2026-10-06T09:00:22Z COMMIT: b8137433b chore(release): 2.0.0-alpha.38 Money and Waiting → review+deps dispatched
- 2026-10-06T09:00:44Z PUSH: nz-glass @ b8137433b
- 2026-10-06T09:00:45Z COMMIT: b8137433b chore(release): 2.0.0-alpha.38 Money and Waiting → review+deps dispatched
- 2026-10-06T09:01:29Z COMMIT: b8137433b chore(release): 2.0.0-alpha.38 Money and Waiting → review+deps dispatched
- 2026-10-06T09:01:39Z COMMIT: 0b377f014 docs(handoff): alpha.38 released → review dispatched
- 2026-10-06T09:01:49Z PUSH: nz-glass @ 0b377f014
- 2026-10-06 alpha.38 "Money and Waiting" released (tag v2.0.0-alpha.38): duplicate claims refused per line, near ones warned on Desk+Nadi (names filtered by read permission); approver away -> backup after 2 working days (full-day leave only, one message per person); cancel notices via on_cancel hooks (live site needs migrate to refresh the hook cache); SOP editor (TextEditor, no image button, who-sees line, staff preview); offline/unreachable wording + form-only "what you typed is still here"; "You can't open this." in FormView, refusal toast unless a visible [data-no-access]; four parts show ResourceError; must-read not confirmable unseen; approver report probe: no leak.
DEAD END: re-pointing ~/.claude/hooks at humanless-pipeline would drop /opt/keel work (forked at 75e46ca, ~70 commits each way); /opt/keel is root-owned.
DEAD END: frontend/tests/*.mjs is run by no gate: red since 5 Oct (OT prefill) and 6 Oct (alpha.37 reload wait), fixed by hand. Run it manually before each commit until the gate does.
DEAD END: deploy-gate blocks any shell command whose text contains the word "deploy" (even in a heredoc file body): write such files with the Write tool.
NEXT: owner puts alpha.35-38 live (then migrate); tickets open: loudRequest split, api/__init__ split, expense_claim validate, session hotspot.
DEAD END: K1 (pipeline consolidation) CANCELLED by the owner, 6 Oct: "keel isnt ours to modify or push or merge. so we just focus on this nadi." Never copy, merge, modify or push keel or the pipeline repos. Leftovers ~/keel and ~/hp-k1 (branch k1/consolidate) deleted with the owner's yes, 6 Oct; /opt/keel untouched. Until a gate runs frontend/tests, run `node --experimental-test-module-mocks --test tests/*.test.* tests/**/*.test.*` in frontend/ by hand before each commit.
NEXT: wait for the owner's next Nadi task.
- 2026-10-06T09:45:19Z COMMIT: b64d73795 docs(plans): K1 cancelled by the owner; the next step is the next Nadi task → review dispatched
- 2026-10-06T09:46:40Z COMMIT: b3d25e407 docs(plans): the K1 leftover copies are deleted → review dispatched

2026-10-07T01:49:29Z RULINGS: alpha.39 roster — R1a day marker (Roster Day), R2a off-day punches = OT flat 2x, R3a each field saves alone, R4a HR may re-type a worked day.
2026-10-07T01:49:29Z NEXT: D1 day marker — Roster Day doctype + set_day_type API + _classify_day reads it; Nadi Assign shift optional.
- 2026-10-07T01:50:12Z COMMIT: bd8ac1e1d docs(plans): alpha.39 roster plan approved with the owner's four rulings → review dispatched
- 2026-10-07T01:51:40Z COMMIT: 23909227f docs(plans): alpha.39 plan amended from review: marker precedence, readers, no-shift punch → review dispatched
- 2026-10-07T01:53:08Z COMMIT: 1a6bd1751 docs(plans): alpha.39 plan names where pay reads the day marker → review dispatched
2026-10-07T02:20:46Z EVIDENCE: 2 correct — test_roster_day 29/29, test_roster_day_type 13/13, test_off_day_marker_punch 3/3; red on HEAD code: 6F+18E, 3F, 1F.
2026-10-07T02:20:46Z EVIDENCE: 3 works — 29 pay/roster stub files green; test_shift_supervisor_rosters_own_team 1 fail is pre-existing on HEAD (Attendance row fence), not D1.
- 2026-10-07T02:20:58Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 11 file(s) ⟂a204f4f4a3bd
- 2026-10-07T02:20:58Z EVIDENCE: 3 works — blast radius green: 19 dependent(s), 11 extra test file(s) ⟂145db77564d9
- 2026-10-07T02:21:03Z COMMIT: ee44ec9fc feat(roster): HR can mark a day Off with no shift → review dispatched
2026-10-07T02:21:52Z NEXT: D1b (Nadi Assign shift optional, worker writing .claude/tmp/d1b-result.md) -> review diff, vitest red/green, live on fresh.local as HR, commit; read D1 review of ee44ec9fc; then D2 edit-in-place.
- 2026-10-07T02:22:08Z COMMIT: b7ed16705 docs(plans): alpha.39 progress — D1 server landed, D1b in flight → review dispatched
- 2026-10-07T02:27:40Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-07T02:27:41Z COMMIT: 212e84af6 fix(roster): a Shift Supervisor could read every company's day markers → review dispatched
2026-10-07T02:28:49Z EVIDENCE: 2 correct — D1b team-roster-assign 24/24 (red on HEAD: 8 fail), eslint clean.
2026-10-07T02:28:49Z EVIDENCE: 5 looks right — NOT RUN: local dev site lacks the Roster Day table and the site update was refused by the infra gate (pending record 20261007022835). Live HR check waits.
- 2026-10-07T02:28:57Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-07T02:28:59Z COMMIT: 29a995f8c feat(pwa): HR can save an Off day in Nadi Assign without picking a shift → review+design dispatched
- 2026-10-07T02:30:35Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-07T02:30:43Z COMMIT: 224c571cc fix(pwa): Nadi Assign said nothing when Save stayed grey with no shift → review+design dispatched
2026-10-07T02:43:59Z EVIDENCE: 5 looks right — live on fresh.local as HR (390px): no-shift cell -> Assign grey until Day type, hint shown, Location hidden; Off day -> toast "Off day saved for 20 Oct"; Roster Day row written by HR; _classify_day=off. Console: only socket.io refused (local realtime server not running). Test row removed.
2026-10-07T02:43:59Z NEXT: owner ruling on Work Day with no shift (recommend: refuse); then D2 edit in place.
- 2026-10-07T02:44:11Z COMMIT: 594685f66 docs(plans): alpha.39 D1 checked live on the local site as HR → review dispatched
- 2026-10-07T02:49:20Z PLAN: approved 3babe6ed3d5c — # Release 2.0.0-alpha.39 "Roster in HR's Hands" (approved 7 Oct 2026: owner ruled R1a R2a R3a R4a)
- 2026-10-07T02:49:30Z COMMIT: ccf839256 docs(plans): alpha.39 owner rulings: one-day location keeps the split, no Work Day mark → review dispatched
- 2026-10-07T02:50:51Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 5 file(s) ⟂5d9cef17ceeb
- 2026-10-07T02:50:55Z COMMIT: 0c799c0bd fix(roster): a day with no shift could be marked Work Day → review+design dispatched
- 2026-10-07T03:16:23Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-07T03:16:25Z COMMIT: 29a84584a feat(roster): one roster field changes without re-sending the rest → review dispatched
- 2026-10-07T03:21:15Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-07T03:21:16Z COMMIT: 86d028814 fix(roster): a cancelled shift assignment could still change location → review dispatched
2026-10-07T03:23:42Z EVIDENCE: 2 correct — D2 screens: Nadi team-roster-assign 35/35, Desk ShiftAssignmentDialog 25/25 (each red 8 on HEAD); eslint clean (frontend).
2026-10-07T03:23:42Z EVIDENCE: 5 looks right — live as HR: day sheet location-only change on 21 Oct -> only that day moved, shift and neighbours kept; test data removed.
- 2026-10-07T03:23:46Z EVIDENCE: 2 correct — mapped tests green (bun ) for 5 file(s) ⟂99296e5bb39c
- 2026-10-07T03:23:48Z COMMIT: 9f59dae7e feat(roster): Desk and Nadi save one roster field without a refusal → review+design dispatched
- 2026-10-07T03:25:03Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 6 file(s) ⟂b1aa65dc91c9
- 2026-10-07T03:25:04Z EVIDENCE: 3 works — blast radius green: 1 dependent(s), 1 extra test file(s) ⟂625bfdf0dc98
- 2026-10-07T03:25:05Z COMMIT: 874619e77 fix(roster): Desk could still store a Work Day mark on a day with no shift → review dispatched
- 2026-10-07T03:25:45Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-07T03:25:48Z COMMIT: 89fc2e064 fix(roster): Desk half-saved when the new end date fell before the changed day → review+design dispatched
- 2026-10-07T03:26:50Z EVIDENCE: 2 correct — mapped tests green (bun ) for 6 file(s) ⟂2216a7693f49
- 2026-10-07T03:26:52Z COMMIT: 865201245 fix(roster): a grey Save or a refused end date did not say what to do → review+design dispatched
- 2026-10-07T03:28:02Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-07T03:28:04Z COMMIT: fba1360dd fix(pwa): a cleared From date left Save grey with the wrong hint → review+design dispatched
- 2026-10-07T03:29:14Z EVIDENCE: 2 correct — mapped tests green (bun ) for 2 file(s) ⟂758fda180142
- 2026-10-07T03:29:16Z COMMIT: f035843d2 fix(pwa): with a shift picked and no date, Save was grey with no reason → review+design dispatched
2026-10-07T04:00:22Z EVIDENCE: 2 correct — D3 test_roster_worked_day_type 22/22 (red on HEAD: 11 fail); 8 roster/pay files green.
2026-10-07T04:00:22Z EVIDENCE: 3 works — bench fresh.local (real Frappe, rolled back): HR re-types worked FIRST day 28 Sep -> assignment keeps it as Off Day, 29 Sep-2 Oct new assignment None, one remark queued hr_asked=True, _classify_day off/normal; supervisor -> "Ask HR". Test data removed.
- 2026-10-07T04:00:31Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-07T04:00:34Z COMMIT: 142d3eb8e feat(roster): HR can change the Day Type of a day that has punches → review dispatched
- 2026-10-07T04:05:50Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-07T04:05:53Z COMMIT: 28fd9beeb fix(roster): re-sending the same Day Type re-marked every worked day → review dispatched
2026-10-07T04:24:27Z EVIDENCE: 2 correct — D4 markers_shown 16/16 (red on HEAD 14), Nadi 42/42 (red 2), Desk 31/31 (MonthViewTable red 4); ruff/eslint clean.
2026-10-07T04:24:27Z EVIDENCE: 5 looks right — live as HR (390px): 20-21 Oct marked Off with no shift show "O" and aria "No shift, Off day"; 22 Oct blank; tap prefills Day type Off Day. Bench: supervisor get_day_markers returns own line only, an outsider marker hidden. Test data removed.
- 2026-10-07T04:24:32Z EVIDENCE: 2 correct — mapped tests green (pytest bun ) for 8 file(s) ⟂f5cc77a393ea
- 2026-10-07T04:24:32Z EVIDENCE: 3 works — blast radius green: 2 dependent(s), 1 extra test file(s) ⟂2b4564685e81
- 2026-10-07T04:24:35Z COMMIT: d93c4ab49 feat(roster): the roster shows a day off with no shift, and a swap keeps Day Types → review+design dispatched
- 2026-10-07T04:26:48Z EVIDENCE: 2 correct — mapped tests green (bun ) for 4 file(s) ⟂4ccc22c38833
- 2026-10-07T04:26:51Z COMMIT: ebe7a3e26 fix(roster): a no-shift day off read twice in Nadi and had no name in Desk → review+design dispatched
- 2026-10-07T04:27:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-07T04:27:57Z COMMIT: b5c7edd91 test(roster): pin that clearing a day marker still re-marks the worked day → review dispatched
- 2026-10-07T04:29:56Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-07T04:29:58Z COMMIT: 89b29f186 fix(roster): a shift dragged onto a marked day off still paid as a day off → review dispatched
2026-10-07T04:30:54Z NEXT: alpha.39 built and reviewed (bd8ac1e1d..89b29f186), not pushed. Waiting on owner: (1) push + release; (2) should day sheet / Team status read Roster Day markers (ticket-team-py-member-statuses.md). Desk month view + drag-swap not checked live.
- 2026-10-07T04:30:58Z COMMIT: 4870f0078 docs(plans): alpha.39 built and reviewed; release waits on the owner → review dispatched
2026-10-07T04:45:55Z EVIDENCE: 3 works — pre-release: frontend 1562/1562, Desk 30/30; 123 py test files touching pay/check-in/roster run one by one: alpha.39 broke one (test_ot_holiday_classification strict fake DB, fixed). 6 files fail identically on alpha.38 code (pre-existing: replayed_tap 8, restamp 5, attendance_health 1, checkin_session_rules 1, sync_runner 1, shift_supervisor_rosters_own_team 1).
- 2026-10-07T04:46:06Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 2 file(s) ⟂e6004e8cb4c1
- 2026-10-07T04:46:10Z COMMIT: 704bcfd38 test(ot): the holiday-calendar tests refused the new day-marker read → review dispatched
- 2026-10-07T04:46:48Z COMMIT: 403539ff2 chore(release): 2.0.0-alpha.39 Roster in HR's Hands → review+deps dispatched
- 2026-10-07T04:47:40Z COMMIT: 4dff516c0 fix(release): About this app showed "Honest Leave Balances" since alpha.27 → review+deps dispatched
- 2026-10-07T04:50:11Z COMMIT: 9bb929c37 docs(handoff): alpha.39 released → review dispatched
- 2026-10-07T06:41:29Z PLAN: approved cfb64c08cef6 — # Release 2.0.0-alpha.39 "Roster in HR's Hands" (approved 7 Oct 2026: owner ruled R1a R2a R3a R4a)
2026-10-07T06:44:07Z EVIDENCE: 2 correct — D5 now_default_shift 8/8, calendar_team_matches_team_page 7/7 (red on HEAD: 2); 39 affected files, only pre-existing failures (fenced 2, checkin_session_rules 1, same on HEAD).
2026-10-07T06:44:07Z EVIDENCE: 3 works — bench fresh.local (rolled back): 22 Oct Team status Scheduled -> Off, day-sheet shift Nadi W0 Day -> none after marking Off.
- 2026-10-07T06:44:14Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 7 file(s) ⟂8ac8c021b707
- 2026-10-07T06:44:14Z EVIDENCE: 3 works — blast radius green: 11 dependent(s), 8 extra test file(s) ⟂2fe864bb96a3
- 2026-10-07T06:44:17Z COMMIT: fe2e61dad feat(team): a day HR marked off shows as off on Home, the day sheet and Team → review dispatched
- 2026-10-07T06:47:37Z COMMIT: d62b512bc docs(plans): Team status ticket records the day-marker follow-ups → review dispatched
2026-10-07T07:04:22Z NEXT: owner to decide (1) Desk-form shift on a marked day clears the marker (hand-made only, not splits)? (2) release fe2e61dad as alpha.40 now or hold. 2 commits ahead of origin, not pushed.
- 2026-10-07T07:04:30Z COMMIT: ea22880ec docs(plans): next step waits on two owner calls → review dispatched
2026-10-07T07:05:06Z NEXT: owner decides Desk-form shift on a marked day + alpha.40 release of fe2e61dad; 3 commits unpushed.
- 2026-10-07T07:05:09Z COMMIT: ec4a3f4ec docs(plans): session end, NEXT recorded → review dispatched
2026-10-07T07:21:58Z EVIDENCE: 2 correct — shift_assignment_hooks 11/11 (red on HEAD: 6); 39 related files, only pre-existing failures (restamp 5, attendance_health 1).
2026-10-07T07:21:58Z EVIDENCE: 3 works — bench fresh.local (rolled back, hook cache cleared): Desk-form shift on 4 Nov removes only that mark; a roster split over a marked 10 Nov keeps it; no circular import.
- 2026-10-07T07:22:02Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 5 file(s) ⟂a3a4f7ac8d73
- 2026-10-07T07:22:02Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 2 extra test file(s) ⟂add7c1e7c916
- 2026-10-07T07:22:04Z COMMIT: de84475ac fix(roster): a shift made in the Desk form left the day-off mark under it → review+cross-app dispatched
- 2026-10-07T07:23:18Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 4 file(s) ⟂43f52428a892
- 2026-10-07T07:23:18Z EVIDENCE: 3 works — blast radius green: 3 dependent(s), 3 extra test file(s) ⟂f95945b27b3b
- 2026-10-07T07:23:19Z COMMIT: 86949c3f1 fix(roster): a shift rule's open-ended shift could wipe every future day mark → review+cross-app dispatched
2026-10-07T07:24:56Z EVIDENCE: 2 correct — shift_assignment_hooks 16/16; invariant mutation-checked (untagging shift_rules fails 2). 3 works — bench fresh.local (rolled back): Desk shift on 4 Nov clears only that mark, roster split keeps 10 Nov.
- 2026-10-07T07:24:59Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 3 file(s) ⟂def0d4bb8c36
- 2026-10-07T07:25:02Z COMMIT: 9f61777a3 fix(roster): approving a Shift Request over a marked day could be refused → review+cross-app dispatched
- 2026-10-07T07:27:08Z EVIDENCE: 2 correct — mapped tests green (pytest ) for 1 file(s) ⟂c80ac5cacfbd
- 2026-10-07T07:27:10Z COMMIT: c6cbe29b1 test(roster): the shift-creator guard caught only one way of writing a shift → review+cross-app dispatched
2026-10-07T07:30:41Z EVIDENCE: 3 works — alpha.40 pre-release: 247 test files touching the 7 changed modules, run one by one; every failure identical on alpha.39 code (replayed_tap 8, restamp 5, fenced 2, timezone 2, attendance_health 1, checkin_session_rules 1, sync_runner 1, supervisor_own_team 1).
- 2026-10-07T07:30:46Z COMMIT: efe292f0d chore(release): 2.0.0-alpha.40 Days Off Everywhere → review+deps dispatched
2026-10-07T07:31:52Z NEXT: alpha.40 released (v2.0.0-alpha.40). Owner puts alpha.39 + 40 live and runs migrate. No open rulings.
- 2026-10-07T07:31:58Z COMMIT: 7196e774b docs(handoff): alpha.40 released → review dispatched
- 2026-10-07T07:32:36Z COMMIT: f3aa6f271 docs(plans): progress ledger after the alpha.40 handoff → review dispatched
- 2026-10-07T07:59:59Z PLAN: approved a98a7292d437 — # Release 2.0.0-alpha.41 "Clean Glass" (DRAFT 7 Oct 2026 — awaiting owner approval)
2026-10-07T08:00:17Z NEXT: alpha.41 "Clean Glass" plan drafted (current-plan.md), awaiting owner approval + rulings E1 (Expense words on Desk) and E2 (Android Back fallback).
- 2026-10-07T08:01:27Z PLAN: approved 8a1817154211 — # Release 2.0.0-alpha.41 "Clean Glass" (approved 7 Oct 2026: owner "Approve as written", E1a, E2a)
2026-10-07T08:01:27Z RULINGS: alpha.41 approved as written; E1a Expense Desk words = Nadi; E2a Android Back fallback = keep + note.
2026-10-07T08:01:27Z NEXT: build S1 (gates), S2 (filter words), S4 (FormView error line) in parallel; then S3, S5-S12.
- 2026-10-07T08:01:30Z COMMIT: 458669110 docs(plans): alpha.41 Clean Glass plan approved with the owner's rulings → review dispatched
- 2026-10-07T08:03:28Z PLAN: approved d1bb7f9b3a26 — # Release 2.0.0-alpha.41 "Clean Glass" (approved 7 Oct 2026: owner "Approve as written", E1a, E2a)
- 2026-10-07T08:07:00Z PLAN: approved d1bb7f9b3a26 — # Release 2.0.0-alpha.41 "Clean Glass" (approved 7 Oct 2026: owner "Approve as written", E1a, E2a)
- 2026-10-07T08:07:01Z EVIDENCE: 2 correct — mapped tests green (bun ) for 7 file(s) ⟂2500172f42c8
