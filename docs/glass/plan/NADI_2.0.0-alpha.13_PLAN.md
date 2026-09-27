# Nadi 2.0.0-alpha.13 — plan (26 Sep 2026)

**Goal.** Finish what alpha.12 carried over and make the app feel alive in the places people use every day: a request that shows its story, a Calendar that sums the month, notifications you can read in one glance, a lighter first download, and Apple-style feedback on the actions people take most.

Same rules as alpha.12: Apple first (`docs/glass/audit/2026-09-26-a12/rules.md`), measured before and after, one cause per commit, red test first, the 7-audit iOS gate at 0, and the owner deploys.

---

## Evidence gathered 26 Sep 2026

| Item | What is there today | What it means |
|---|---|---|
| Notifications | 217 rows on the test site: Leave 117, Expense 31, Fix a day 28, Shift 27, OT 14. Each has `from_user` + `reference_document_type` + `reference_document_name`. Already grouped by day (Today / Yesterday / Earlier), 20 a page, "Mark all read" exists. No way to mark one group read. | Grouping by person and kind needs no schema change; "mark this group read" needs one small endpoint. |
| Request timeline | All five request doctypes have `track_changes: 1`. Version rows record who and when: `status Open → Rejected, docstatus 0 → 1, by nadi.w0.approver, 24 Sep 17:58`. Remote check-in also has `approved_at`. | A timeline can be read from existing history. No new fields, no backfill. |
| Calendar summary | `get_month_flags` already returns `paired` (worked days) and per-day `needs_you` flags. | "18 days worked · 2 to fix" can be computed from the payload the screen already loads. No server change. |
| First download | Main JS 654 KB (after alpha.12). Ionic's biggest parts that load up front: modal 68 KB, popover 53 KB, alert 45 KB, refresher 41 KB, nav 31 KB, action sheet 26 KB. Alert is used in ONE place (a Profile error), action sheet in ONE (a workflow menu). | Replacing those two with the app's own sheet or toast lets alert and action-sheet code drop out; target is main JS under 550 KB, first paint under 5 s on the slow-phone profile. |

---

## Slices (in order; one cause per commit)

### 1. Request timeline on every sent request
- **What you see:** under the request, a short list, newest last:
  - "Sent · Wed 24 Sep, 9:12 am"
  - "Rejected by W0 approver · Wed 24 Sep, 5:58 pm"
  - Each row has a status mark: a tick for approved, a cross for rejected, a clock for waiting.
- **Source:** one read-only endpoint, `hrms.api.request_history(doctype, name)`. It returns `[{what, who_name, when}]` from Version rows, only for status and docstatus changes. It is fenced like the request itself: the owner, their approver, and HR can read it; nobody else.
- **Words:** people's names, never emails. "Sent", "Approved", "Rejected", "Cancelled", "Withdrawn".
- **Checks:** a pure mapping test on real Version JSON; a permission test (a stranger gets 403); a bench probe on the test site.

### 2. Calendar month summary
- **What you see:** one line above the grid, "18 days worked · 2 to fix". Tapping "2 to fix" shows those days.
- **Source:** the payload already loaded (`paired`, `needs_you`). No new request.
- **Checks:** a pure count test; a WebKit screenshot at 402 and 1280.

### 3. Notifications you can read at a glance
- **What you see:** inside each day group, the same person and kind fold into one row: "W0 employee asked for time off · 3". Tap to open the three. The newest message leads. Swipe or a trailing button marks the whole group read.
- **Source:** grouping on the client (`from_user` + `reference_document_type`). A new endpoint `mark_notifications_read(names)`, POST-only, can only mark the caller's own rows.
- **Checks:** a grouping test; a permission test (someone else's row is refused); a mark-read round trip on the bench.

### 4. Lighter first download
- Replace the one `alertController` (the Profile error) with the app's toast, and the one `ion-action-sheet` (the workflow menu) with the app's own GActionSheet.
- Load the pull-to-refresh and popover code only when used.
- **Target, measured on the same profile as alpha.12:** main JS under 550 KB, first paint under 5 s.

### 5. Apple feedback on the actions people take most
Same rules as the Today card (`mockups/mockup-nadi-apple-way.html`): once, for a reason, stopped by Reduce Motion.
- **Approve or reject:** the row's tick or cross draws itself, then the row slides out of the list.
- **Numbers that change** (leave left, overtime hours, the unread count) roll to their new value instead of jumping.
- **Buttons** dim briefly when pressed, as iOS buttons do (Apple buttons: a pressed state always).
- **Mockup first:** `mockups/mockup-nadi-a13-feedback.html`, for owner sign-off before code.

### 6. Found along the way
Any defect the audits or the bench turn up, one slice each, with a red test.

---

## Out of scope (owner's call, not touched)
- Historical attendance repair, schema or policy changes.
- The Script Report fencing project (deferred 13 Sep).
- Anything that shows or celebrates overtime before it is approved.

## Pipeline
Plan (this file) → mockup for slice 5 → slices 1–4 red → green, committed one by one → slice 5 after sign-off → iOS gate (7 audits) at 0 + states audit → full visual re-baseline → bump to 2.0.0-alpha.13 + changelog → `scripts/release.sh` (tag, push, GitHub Release) → the owner deploys.

## Rulings needed
- **R5** Timeline: show the approver's reject reason in the timeline (the employee already sees it), yes?
- **R6** Notifications: fold the same person and kind within a day (recommended), or fold by kind only?
- **R7** Slice 5 feedback: approve the mockup before I build it (it will be ready with the first slices).
