# Nadi 2.0.0-alpha.6 — the plan

**Goal (owner, 24 Sep 2026):** every employee, approver, team leader and manager can use Nadi **correctly**
(it works with the Desk setup HR already has), **smoothly** (UX: plain words, few steps, no confusion) and it
**looks and feels like an Apple app** (UI: iOS 26 / Liquid Glass, Apple rules only).

**Ground rules**
- Nadi adapts to the backend as it is. We never change the backend to make a screen work. A real backend **bug** still gets fixed, and it is named as a bug.
- Every change has a source (Apple, NN/g, GOV.UK, or a measurement on the running app), a test that failed first, and one commit.
- Owner rulings are the top authority. Then the rulebook. Then my judgment, and I say when I'm using it.

## The documents (all in `docs/glass/plan/`)

| File | What it is |
|---|---|
| `alpha6-research.md` | Apple / NN/g / GOV.UK rules, one URL per rule (Apple's text read in full through its JSON feed) |
| `alpha6-standard.md` | The rulebook: about 90 rules with IDs (G, T, L, R, K, B, N, S, M, W, P) |
| `alpha6-pages.md` | Every screen: purpose, contents, actions, states, what's wrong today, measured violations (§F) |
| `alpha6-field-map.md` | Every Desk field on every request: shown, filled for them, or hidden (helper output, verified header) |
| `alpha6-readiness.md` | Which Desk setup gaps Nadi already detects for HR, and which it doesn't |
| `alpha6-audit-summary.json` | Raw numbers from the whole-app measurement (197 views) |

## Owner rulings used (24 Sep)
Q1 "Send to {name}" instead of Save: **yes**. Q2 headings: **delegated → grey**. Q3 not scroll, the page drags sideways (Time off).
Q4 Posting date: **delegated → hide** (each expense item has its own date). Frontend adapts to the backend.

## Steps

Status: ✅ done (commit) · ▶ next · ◻ to do. "Evidence" = how we know it's broken or done.

### Phase 0 — Know the truth (done)
| # | Step | Evidence | Status |
|---|---|---|---|
| 0.1 | Research Apple rules | alpha6-research.md | ✅ 7e08cca24 |
| 0.2 | Write the rulebook + page contracts | alpha6-standard.md, alpha6-pages.md | ✅ 7e08cca24 |
| 0.3 | Measure every screen | 197 views, 0 errors (alpha6-audit.mjs) | ✅ 7e08cca24 |
| 0.4 | Every request type, staff → approver, server rules | 87 checks, 0 fail (journey_every_request.py) | ✅ 1bc64c46f |
| 0.5 | Same, through the real screens | 8 steps, 0 fail (alpha6-journey.mjs) | ✅ c3dd82d59 |

### Phase A — Works correctly (bugs first)
| # | Step | Evidence it's broken | Source | Status |
|---|---|---|---|---|
| A0 | Approval sheet shows the date | screen journey: Fix a day sheet had no date | W6, owner "correctly" | ✅ 45f1d5efb |
| A1 | Overtime through the screens | 10/10: all 5 types, both decisions each way | 0.5 gap | ✅ fb716211b |
| A2 | Home "No shift today" when Profile shows a shift | Home reads only assignments (`api/now.py:65`), Profile the default shift (`Profile.vue:321`) | your screenshot | ✅ 1d0a08320 |
| A3 | Time off page drags sideways on iPhone | Safari ignores a date field's width without `appearance:none; min-width:0`, and Chrome can't show it | WebKit bug, 3 sources | ✅ c501578fc |
| A4 | Empty section headings (6 on Expense, "Other details" on Time off) | audit §F | R7, W1 | ✅ 88bc8706f |
| A5 | Approver pickers show emails ("x@y.com : Name") | screenshots | K3, W10 | ✅ 175028d53 |
| A6 | Expense sheet shows 2 statuses (Draft + Waiting) and ERP totals | screen journey shot 17 | W1, R2 | ✅ d9457d894 |
| A7 | HR setup check for the 4 gaps Nadi doesn't detect (expense account, payable account, leave year, shift overtime) | alpha6-readiness.md; each one broke a request on the test site | "never ask employees to diagnose" | ✅ a6dc6dc29 |

### Phase B — One Apple look (UI)
| # | Step | Evidence | Rule | Status |
|---|---|---|---|---|
| B1 | One field style (6 looks today → 1) | audit: 48/0, 49/0, 64/0, 44/12, 48/12, 50/12 | K1, L7 || ✅ |
| B2 | Forms as grouped lists (label left, value right) | screenshots | K2, R1 || ✅ |
| B3 | Switches in rows, on the right, hint below the group (Settings, Half day) | Profile screenshot | TOG, R4 || ✅ |
| B4 | Type: the iOS scale only, no extra-heavy weight, no 10px text | 8 off-scale sizes, weight 800 on 41 screens, 10px tab labels | T1, T2, T4 || ✅ |
| B5 | Lime only on the one button that acts. Headings go grey. | lime headings on 21 screens | G5, G6 || ✅ |
| B6 | Buttons: 8 heights → 3 (large, regular, small) | 41–61px measured | B5, L4 || ✅ |
| B7 | New request sheet: icon, title, one-line hint, separators | your screenshot | S6 || ✅ |
| B8 | Sheets: × on the left, action on the right, grabber, swipe to close | sheet review | S2, S3 || ✅ |

### Phase C — Smooth (UX + words)
| # | Step | Evidence | Rule | Status |
|---|---|---|---|---|
| C1 | Plain words (20+ ERP terms), plus a gate that blocks them | audit jargon list | W1, W4 || ✅ |
| C2 | "Send to {name}" instead of Save on requests | 7 forms | B4, ruling Q1 || ✅ |
| C3 | Overtime: 5 open days, then "Show more". Past days folded away. | your screenshot | R6 (NN/g) || ✅ |
| C4 | Long lists (notifications 30, history): a few, then "Show all" | audit | R6 || ✅ |
| C5 | One tap target size (5 underlined web links → rows) | audit <44px | L4, R3 || ✅ |

### Phase D — Feels native (motion + PWA)
| # | Step | Evidence | Rule | Status |
|---|---|---|---|---|
| D1 | Record every page change and sheet; fix any that skip, double or flash | not yet recorded | M1–M8 || ✅ |
| D2 | No grey tap flash, no text selection on controls, no pull-down overshoot showing another colour | none set in the theme | P1–P3 || ✅ |

### Phase E — Prove and ship
| # | Step | Status |
|---|---|---|
| E1 | Re-run the whole-app audit: every counter in alpha6-pages.md §F at 0 || ✅ |
| E2 | Re-run both journeys (server 87 checks + screens) || ✅ |
| E3 | Complete coverage: 52 routes, 38 sheets and menus, each state (empty / error / long), sizes 320 / 390 / 430 / desktop. Each row is **measured**, **not applicable (why)** or **missing** || ✅ |
| E4 | All design gates, all tests, tag `v2.0.0-alpha.6`, push. **You deploy.** || ✅ |

## Honest limits
- **Real Safari:** this machine can't run it until `sudo npx playwright install-deps webkit` is run once. Until then, A3 is fixed from documented evidence and checked on your phone after deploy.
- **Apple publishes no numbers** for side margins or animation timing. Where the rulebook says "Nadi token", that's our choice, not Apple's.
- **Only 2 real test people** (staff + one approver) plus the W0 manager and HR on the local site. Live data may show cases these don't.

## Order and size
A (8 steps) → B (8) → C (5) → D (2) → E (4) = **27 steps. 27 done.** Evidence per phase: git log v2.0.0-alpha.5..v2.0.0-alpha.6; coverage in `alpha6-coverage.md`. One commit each, tested before it lands.
