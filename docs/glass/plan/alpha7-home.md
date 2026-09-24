# Nadi Home — what it shows today, and an iOS 26 Home proposal (alpha 7 research)

Read-only. No repo edits. Every claim has a URL. Anything marked **(inference)** is my reasoning, not a source.

---

## 0. What Home shows TODAY, top to bottom (code-read, 24 Sep 2026)

File: `/home/nabil/nz-version-16/frontend/src/views/Home.vue` (one 720px column, `gap-5`, pull-to-refresh).
Screenshot of the live screen: `/tmp/alpha7/nadi-home.png` (dark, lime accent).

| # | Block | What the person sees | Data source |
|---|---|---|---|
| — | Header (BaseLayout/ShellHeader) | Nadi "n" mark, bell with unread dot, avatar | shell |
| 1 | **NowBar** (`components/NowBar.vue`) | Date line "Thursday, 24 September"; coloured dot + state: **Working · 3h 12m** / **Done for today** / **Not checked in** / **No shift today**; detail line "Nadi W0 Day · 09:00–18:00" or "Checked out at 6:02 pm". Ticks once a minute. Error: "We couldn't load today…" | `hrms.api.now.get_now` via `data/now.js` (`nowResource`, personal cache). State key/label chosen server-side in `hrms/api/now.py` (working/done/before/off) |
| 2 | **CheckInPanel** (`components/CheckInPanel.vue`) | (a) Warning banner only if an old IN is still open: "Forgot to check out from …?" / "HR flagged your … check-in as abandoned" + "Resolve" → LateCheckoutDialog. (b) One full-width lime **Check in / Check out** button. (c) "You need signal to check in." when offline. (d) If mobile check-in is off: just a date line (a **second** date on the screen). | `hrms.api.get_hr_settings`; `Employee Checkin` list (last log decides IN/OUT; >16h open = stale); `hrms.api.remote_checkin.get_unresolved_stale_in` |
| 2b | Check-in **sheet** (GModal, opened by the button) | Eyebrow + big clock "02:56 pm" + date; **location verdict** ("You're at X — within range", "Too far from X", "Location uncertain", "Free location", "No check-in area set"); live selfie camera; "Confirm Check in" button. Remote/strict rejection dialogs after submit. | `navigator.geolocation.watchPosition`; `hrms.api.geofence.get_active_shift_location` / `check_geofence`; `hrms.api.remote_checkin.punch` + `upload_selfie` |
| 3 | **Announcements** (`components/Announcements.vue`) | Eyebrow "Announcements"; up to **2** list rows (icon by category, title, "Needs your confirmation" or "2 days ago", badge New/Confirm). Empty: "No news." Error sentence. | `hrms.api.announcements.home_announcements` (`HOME_LIMIT = 2`, unread + needs-ack + pinned first); opening a card marks it read (`get_announcement`) |
| 4 | **Your week** panel (GListPanel with 2 rows) | Row 1 **HomeWeek**: "0 days worked" / "2h 00m overtime to claim" (tappable when OT > 0). Row 2 **HomeComingUp**: next leave/trip, or "Nothing booked. Next public holiday: …" | `hrms.api.home.get_home_week`, `hrms.api.home.get_home_coming_up` (`data/home.js`) |
| 5 | **NeedsYou** (`components/NeedsYou.vue`) | Only for approvers or when something waits. Eyebrow "Needs you"; one row per kind (approvals, remote check-ins…), 3 then "show all". Empty: "Nothing waiting on you." | `hrms.api.needs_you.get_needs_you` + `pendingCountResource` (`data/remoteCheckin`); `isApprover` (`data/team`) |

**Why it reads "bland" (inference, from the screenshot + code):**
- Everything is the same weight: eyebrow → grey sentence → list panel, five times. No block is visually "the hero".
- The state ("Not checked in") and the action (button) are two separate things with air between them. They are one idea.
- The geofence verdict — the thing people worry about — lives only inside the sheet. Home says nothing about "am I in the area".
- On an approver's phone, "Needs you" is **last**, below the fold.
- Empty states are bare grey lines ("No news.", "Nothing booked.") and take a full block each.

---

## 1. Apple's own "today" screens — patterns worth copying

| Pattern | What Apple does | Source |
|---|---|---|
| **One hero, then cards** | Fitness Summary opens on the Activity rings; the rest is a list of metric cards people can add/move/remove ("Edit Summary"). | https://support.apple.com/guide/iphone/see-your-activity-summary-iph4c34a8a95/ios |
| **Pinned first, highlights after** | Health Summary: "Pinned" categories show how you're doing *today*; "Highlights" below; tap for detail. | https://support.apple.com/guide/iphone/view-your-health-data-iphe3d379c32/ios , https://support.apple.com/en-us/104997 |
| **Status tiles under the title** | Home app: "below your home's name, buttons show the status of accessories… e.g. Lights '3 on'". Then Cameras, Scenes, Favorites, Rooms. | https://support.apple.com/guide/iphone/intro-to-home-iph22d98bbca/ios , https://support.apple.com/guide/iphone/control-accessories-iph0a717a8fd/ios |
| **Title + subtitle answer the question before the detail** | HIG Charts: Weather "provides a title and subtitle that succinctly describe the expected precipitation… giving people the most important information without requiring them to examine the details". | https://developer.apple.com/design/human-interface-guidelines/charts |
| **Weather: big number, then modules** | Current temp large at top, "feels like" right below it; iOS 27 adds a Highlights section at the top. | https://support.apple.com/guide/iphone/check-the-weather-iph1ac0b35f/ios , https://www.macrumors.com/guide/ios-27-weather/ |
| **Wallet pass: header / primary field** | "Header fields: Show critical information that remains visible when the pass is collapsed." "Primary field: Shows the most important information people need." | https://developer.apple.com/design/human-interface-guidelines/wallet |
| **Live Activity = a running state** | "Focus on important information that people need to see at a glance." Timer app's minimal presentation "displays the remaining time instead of a static icon". Works best for activities "that don't exceed eight hours". Interactive elements only for "essential functionality… that people activate once or temporarily pause and resume". Numeric content transitions for changing numbers. | https://developer.apple.com/design/human-interface-guidelines/live-activities |
| **Widgets = glanceable, one focus** | "timely, glanceable content"; "Sparse layouts can make the widget seem unnecessary, while overly dense layouts are less glanceable"; "essential information at a glance… additional details by taking a longer look"; "avoid creating app-like layouts". "Convey meaning without relying on specific colors." | https://developer.apple.com/design/human-interface-guidelines/widgets |

### What the check-in card should be MADE of (the key rule)

- HIG Materials: "Liquid Glass forms a distinct functional layer for controls and navigation elements… that floats above the content layer." **"Don't use Liquid Glass in the content layer."** "Instead, use standard materials for elements in the content layer." "Use Liquid Glass effects sparingly… Limit these effects to the most important functional elements." Source: https://developer.apple.com/design/human-interface-guidelines/materials
- WWDC25 "Get to know the new design system": Liquid Glass is "a new functional layer… floating above your content… without ever stealing focus"; "apply the material directly to the control, not its inner views"; primary action "separate and tinted". Source: https://developer.apple.com/videos/play/wwdc2025/356/ (notes: https://wwdcnotes.com/documentation/wwdc25-356-get-to-know-the-new-design-system/)
- Buttons: `.glassProminent` "applies a prominent Liquid Glass effect" — https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glassprominent ; HIG Buttons: "use a button that has a prominent visual style for the most likely action in a view", "Keep the number of prominent buttons to one or two per view", "Prefer buttons that span the width of the screen for primary actions" — https://developer.apple.com/design/human-interface-guidelines/buttons

**Answer:** the check-in *card* is content → **standard material / solid grouped surface** (like a Wallet pass or the Fitness rings card). Only the **button inside it** is glass (prominent, tinted). The owner's "Liquid-Glass-style card with a clear separation" is achievable as a **thick standard material** (blurred, rounded, concentric) — that is allowed in the content layer. A lensing/refracting Liquid Glass card would break the Materials rule. **(inference: the owner's intent — "feels like iOS 26, clearly separated" — is met by material + concentric radius + a glass button; it does not need glass on the card itself.)**

---

## 2. Workforce apps: what they put first

| App | First thing on the home/clock screen | Lessons | Source |
|---|---|---|---|
| **Deputy** | Home tab shows your **upcoming shift**; "Start Shift in 'Area'" → shift details → Start Shift. Same screen: start/end **breaks**, **End Shift**. If photo required: "Your photo will be taken" shown *above* the button. | Warn about the selfie **before** the tap. Location recorded only at clock in/out; may be blocked if far away. | https://help.deputy.com/hc/en-au/articles/4614769464207-Start-and-end-your-shift , https://help.deputy.com/hc/en-au/articles/4753097048719-Employee-guide-to-the-Deputy-mobile-app |
| **When I Work** | Dashboard: "quick updates, clock in or out, request time off, take OpenShifts, see who's working". Shift line: "Your Cashier shift at Northeast starts at 12p." | Button hidden/erroring when no scheduled shift or already completed — a known confusion source. | https://help.wheniwork.com/articles/using-the-dashboard-android/ , https://help.wheniwork.com/articles/troubleshooting-mobile-time-clocks/ |
| **Connecteam** | Time Clock at the top of the feed; blue "Start Shift"; "time begins tracking at the top of the screen". Before shift start the button is **greyed out**, and "a minute before… a countdown timer appears". | A disabled button with no reason is their #1 support ticket class ("My users can't clock in!"). | https://help.connecteam.com/en/articles/5826070-time-clock-for-users , https://help.connecteam.com/en/articles/8691720-is-there-a-way-to-prevent-an-employee-from-clocking-in-before-their-shift , https://help.connecteam.com/en/articles/6420237-troubleshooting-my-users-can-t-clock-in-why-could-that-be |
| **Microsoft Teams Shifts** | Time clock: clock in, **Break** (press and hold), Stop; "the in-shift time counter continues". Location: can clock in anywhere but "notified if they're not on location"; 200 m radius. | Elapsed counter is the in-shift hero; confirmation on punch. | https://support.microsoft.com/en-us/office/clock-in-and-out-with-shifts-ae7b676c-7666-46c7-9f68-85ff54acec8b , https://onmsft.com/how-to/how-to-use-shifts-in-microsoft-teams-to-manage-work-hours-schedules-and-more/ |
| **Homebase** | Tap the clock icon, confirm. Geofence: "will only allow clock-in if employees are within the geofence"; outside → blocked with an error. | Blocking message must say *why* (too far). | https://support.joinhomebase.com/hc/en-us/articles/235228167-Mobile-time-clock-on-iOS-and-Android-apps , https://timeero.com/reviews/homebase-review |
| **Workday** | Clock out by tapping "the blue box on your home screen that **shows how long you have been clocked in**". Geofence reminders on enter/exit. | The elapsed-time tile *is* the clock-out control — state and action are one object. | https://finance.southtexascollege.edu/businessoffice/time-tracking/files/Employee-Checking-In-and-Checking-Out-Mobile-App.pdf , https://www.workday.com/en-us/products/workforce-management/time.html |

**Common pattern (inference from the six):** shift window + one big button, and once in: an **elapsed counter** that becomes the hero with the out-action attached. None puts announcements above the clock.

---

## 3. Research: glanceable screens

- NN/g dashboards: operational dashboards "impart critical information quickly… time-sensitive tasks"; use preattentive cues (length, position). https://www.nngroup.com/articles/dashboards-preattentive/
- F-pattern: people read the top lines, then scan down the left edge; "good design can prevent F-shape scanning" (front-load words, left-aligned labels). https://www.nngroup.com/articles/f-shaped-pattern-reading-web-content/
- Progressive disclosure: show "a few of the most important options", the rest on request. https://www.nngroup.com/articles/progressive-disclosure/
- One primary action: HIG "one or two" prominent buttons per view (above). eBay Playbook: "There should only be a single primary action per screen." https://playbook.ebay.com/design-system/components/cta-button
- Cards: "a container for a few short, related pieces of information… a linked, short representation of a conceptual unit". https://www.nngroup.com/articles/cards-component/
- **Banner blindness:** content placed "at the top of the page", large or colourful boxes, gets ignored as ad-like. https://www.nngroup.com/articles/banner-blindness-old-and-new-findings/ — relevant to "announcement on top".
- Empty states: say what is true and give the next step. https://www.nngroup.com/articles/empty-state-interface-design/

---

## 4. iOS details for the web build

| Detail | Rule | Source |
|---|---|---|
| Big state like a Live Activity | "Checked in · 3h 12m" as the card's title; keep the running number large; Live Activities use numeric content transitions for changing numbers. | https://developer.apple.com/design/human-interface-guidelines/live-activities |
| Timer cadence | Current once-a-minute tick is right for "h m" resolution (NowBar comment agrees). Use `font-variant-numeric: tabular-nums` so digits don't jiggle. Pause/refresh on `visibilitychange` (browsers throttle background timers anyway). | https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric , https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API |
| Motion | Honour `prefers-reduced-motion` for any number roll or glass shimmer. | https://web.dev/articles/prefers-reduced-motion |
| Primary action | Full-width, prominent (glass-prominent look), one per view. | https://developer.apple.com/design/human-interface-guidelines/buttons |
| Location line | Small secondary line with a symbol + text ("location.fill  In range · Nadi HQ"); never colour alone. | https://developer.apple.com/design/human-interface-guidelines/widgets (colour rule), https://developer.apple.com/design/human-interface-guidelines/sf-symbols |
| Card vs list row | Card = one conceptual unit with a state (check-in, a pass). List row = one of many similar items (announcements, approvals). HIG Lists: grouped style "uses headers, footers, and additional space to separate groups". | https://www.nngroup.com/articles/cards-component/ , https://developer.apple.com/design/human-interface-guidelines/lists-and-tables |
| Alerts | Live Activities: "Alert people only for essential updates that require their attention." Apply to announcement badges. | https://developer.apple.com/design/human-interface-guidelines/live-activities |

---

## 5. Proposed Home structure

### (a) Staff member — top to bottom

1. **Large title = the date** ("Thursday" large, "24 September" under it), bell + avatar in the glass top bar.
   *Why:* iOS 26 typography "bolder and left-aligned" (https://developer.apple.com/videos/play/wwdc2025/356/); header field idea from Wallet. Replaces NowBar's small date line. Keep ONE date (today CheckInPanel repeats it when mobile check-in is off — remove).

2. **Pinned notice (only when it matters)** — at most **1** row above the card, and only for an **unconfirmed "needs acknowledgement"** or **Urgent** announcement: icon + title + one-line preview + "Confirm". Goes away when confirmed/opened (server already marks read on open).
   *Why:* owner wants news noticed; but banner blindness punishes routine top-of-page boxes (NN/g link above), and the card is the one time-critical job. **(inference)** Routine news stays in block 4.

3. **Today card (the hero)** — standard thick material, concentric radius, NOT Liquid Glass.
   - Line 1 small: shift name + window "Nadi W0 Day · 9:00–6:00".
   - Line 2 large (the state, tabular digits): see states below.
   - Line 3 small, symbol + text: location status.
   - Full-width glass-prominent button, the ONE prominent control on Home.
   - "Your photo will be taken" hint under the button (Deputy pattern).
   - Stale-IN warning ("Forgot to check out from Tue 9:02 am?") moves **inside** the card as its state, not a separate banner.

   | State | Large line | Small line | Button |
   |---|---|---|---|
   | Not in yet | **Not checked in** (or "Starts in 25 min") | Location: "In range · Nadi HQ" / "Checking location…" | **Check in** |
   | In | **Checked in · 3h 12m** (ticks per minute) | "Since 9:02 am · In range" | **Check out** |
   | Done | **Done for today · 8h 41m** | "Out at 6:02 pm" | none; secondary "Fix a punch" text link (or nothing) |
   | Rest day / leave / holiday | **Rest day** / **On leave** / **Public holiday: X** | Next shift "Fri 9:00" | none (or plain "Check in anyway" if policy allows) |
   | Outside area | state as above | **"1.2 km from Nadi HQ — needs approval"** (or "must be within 150 m" when strict) | Check in stays enabled if non-strict (goes to remote approval); strict: disabled **with the reason on the card** (Connecteam/Homebase lesson) |
   | Offline | unchanged | "No signal — you need signal to check in" | disabled + reason |

   *Why:* Workday/Teams make the elapsed tile the hero; Live Activities "focus on the most important information"; Wallet primary field. Moving the location verdict onto Home needs geolocation before the tap — **(inference)** costs battery and a permission prompt on page load; option: show last known verdict from the server, fresh fix only in the sheet.

4. **Announcements** — grouped list, 2 rows (current `HOME_LIMIT`), each with title + **one-line preview** (new: excerpt from body) + age; "See all (n)" row. Unread dot, not a coloured box. Empty: collapse to one quiet row "No new announcements" or hide the block. *(Owner ruled "every block always renders" on 23 Sep — keep a single line, not an eyebrow + line.)*
   *Why:* list rows for many similar items (NN/g cards vs list); progressive disclosure.

5. **This week** — one card like a Fitness metric: "3 of 5 days" big + small "2h 00m overtime to claim ›"; second row "Next: Annual leave 2–4 Oct" / "Nothing booked · next holiday …".
   *Why:* Fitness Summary cards; Weather title-first. Replaces "0 days worked" (a zero headline reads as failure — show "of N scheduled" **(inference)**).

6. **Quick actions — do not bring back.** Evidence: When I Work dashboard carries "request time off" etc. (link above), but Nadi's Requests tab already reaches them in one tap; HIG widgets: "avoid creating app-like layouts"; progressive disclosure. The Home.vue comment records the same decision. If kept at all: one "New request" text row, not a grid.

### (b) Approver — differences only
- Same 1–3.
- **"Needs you" moves to position 4** (above announcements) when count > 0: one grouped list, "Leave · 3", "Remote check-ins · 1", each ›; header shows total. Count also as tab badge. When 0: one line "Nothing waiting on you" at the bottom (current copy).
  *Why:* Health "Pinned" = what needs you today; F-pattern — items below the fold get less attention (NN/g). Today it is last.
- Announcements then This week.

### Removed / merged
- NowBar as a separate strip → merged into the Today card + large title.
- Separate stale-check-out GBanner → becomes a card state.
- Duplicate date in CheckInPanel's "mobile check-in off" branch.
- Eyebrow-per-block chrome (five small grey headers) → iOS grouped-list section headers only where a list has >1 row.

---

## 6. HIG rules a proposal could break (watch list)

1. **Liquid Glass on the check-in card** → breaks "Don't use Liquid Glass in the content layer" (Materials). Use standard material; glass only on the button/bars.
2. **Two prominent buttons** (e.g. Check out + "Take break" both lime) → HIG Buttons "one or two… per view"; keep break/secondary as plain/glass (non-prominent).
3. **Announcement as a coloured box on top** → not an HIG rule but NN/g banner blindness; and Live Activities "alert only for essential updates".
4. **State by dot colour only** (current orange dot) → Widgets "Convey meaning without relying on specific colors" — the text label must stay (it does today).
5. **Per-second ticking seconds** → no HIG ban, but Live Activities/Widgets stress glanceable, and a seconds counter adds motion; respect `prefers-reduced-motion`.
6. **Screen-specific action in the tab bar / bottom accessory** (e.g. putting Check in there) → WWDC25 356: avoid screen-specific actions in the tab bar; `tabViewBottomAccessory` is for app-wide features only (see `/tmp/alpha7/ios26-spec.md` §1).
7. **Disabled button without a reason** → not HIG text, but the top support failure at Connecteam/When I Work (links above).
