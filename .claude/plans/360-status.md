# 360 repair status — 8 September 2026

Source repairs are local only. No production deployment, historical data repair, authenticated acceptance, physical GPS proof or live push delivery is claimed.

| Concern | Current evidence / next work |
| --- | --- |
| Inherited checkout permission denial | ce5ff48dd; fresh and CLI review pass; 9 native framework lifecycle tests, mocked persistence. |
| Settled remote decisions | bf2126a7d; fresh and CLI reviews pass, 12 native lifecycle tests. |
| Duplicate checkout error | e6eb09a35; 6 tests pass in Node and Bun, CLI review pass. |
| Browser account cache / stale session | bb10225ec; 169 frontend tests, lint and both reviews pass. Authenticated multi-tab acceptance pending. |
| Private issue notification recipients | 981c1cbe7; 7 native tests / 96-case matrix plus 75 property examples; fresh and CLI reviews pass. |
| Month-range counting | 09e29ae5d; reviewed correction for raw-work versus approved-claim capacity being integrated. Not complete until capacity and concurrency slices pass. |
| Changed filing identity / amendment bypass | 7548588c0; 16 focused tests, fresh and CLI reviews pass. |
| Claim list / form / saved capacity / rejection | 00a9baa5c; 48 combined tests and fresh review pass. Mixed-shift correction7b7408145 passes fresh and CLI review; concurrency remains active. |
| Late checkout whole-day / auto draft repair | 090091e06 integrated; fresh review and mapped/importer checks pass, native7 repair +12 checkout pass. CLI review also passes. Historical records not yet repaired. |
| OT notification routing | d479e4c05; fresh and CLI reviews pass, 14 native tests. |
| Nonworking days / eligible punch intervals / breaks | ae0028f30 integrates eligible nonworking intervals/status, calendar fixture correction, retained scheduler boundaries and eligible-only links. Fresh re-review PASS,80 tests33subtests plus native DB scenarios. Precision landed (beae4237c); multi-shift rates landed (db22e3dc3 + f7cab99bc); discovery window aligned to filing (29794bc07). Expiry and weekday break follow-ups remain. |
| OT hour persistence precision | Native insert/reload/submit proves decimal(21,2) turns1minute into0.02 and rejects approval. Exact six-field9dp proposal prepared; user authorized implementation/local testing with "proceed". Implementation active, approved local schema verification underway; no production change or historical repair. |
| Concurrent OT decisions / RL grants | 6be841a6e: employee-first row locks in check_if_latest and decide, locking reservation read at approval, current-read duplicates, composite index patch; native two-thread proof on fresh.local (waits, then refused; index used). RL grant concurrency not separately covered. |
| GPS freshness / accuracy / preview parity | 7a4f1161b + 0773ccd72 integrated; 039d134f8 isolated refusal audit (second connection; native test.local 2 passed; review DEPLOY). Device verification still required. |
| PWA and Desk approval capability / stale actions | 6384996d6 integrates reviewed action-specific PWA/Desk controls, dirty/revision guards, self-Leave Reject and legacy Submit. Fresh re-review PASS;195 frontend tests,29 focused Bun tests; integration combined212 frontend pass. |
| OT layout / zero claim / summary races | d58fa94af integrated (header first, one hint, visible 0, per employee/date summary ownership, Save gated with reason); review DEPLOY; frontend 225 pass. |
| New-form dirty state / attachment retry / partial resource failures | Pending PWA recovery slices. |
| Attendance calendar refresh / pending feedback | Pending; historical September rows need read-only diagnosis and a reviewable repair set. |
| Push identity / semantic results / timing / destination / feed access | Remaining notification slices. |
| Desk report scope / aggregate scope / Half Day chart | Remaining report slices. |
| RL allocation mirror ownership / balance conservation | Remaining sync and grant slices. |
| Desk icon / report role / sidebar parity | Remaining metadata repairs; no live migration yet. |
| Broad test harness / E2E reliability | Partly diagnosed; complete suite remains unverified. Existing company-scope failures reproduced on parent. |
| Four-month backdated OT/RL | Work date retained; calendar-month window provisional, existing code uses payroll cycles. Temporary versus permanent availability remains a policy dependency; no expiry assumed or setting enabled. Discovery now covers the full existing filing window (29794bc07); the four-month policy itself remains undecided. |

See the full audit index at docs/glass/audit/2026-09-08-360-audit.md and execution plan at .claude/plans/360-fixes.md. Each pending concern remains in scope; absence of a new user report does not close it.
