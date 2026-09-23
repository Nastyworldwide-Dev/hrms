# App-wide — stuck sheets and glitchy transitions

Status: **DIAGNOSIS + PLAN, no code.** Reported by the owner on 23 Sep 2026:
> tapped a date, the drawer opened, swiped to the next page or minimised really fast without closing it — it stuck. Transitions feel buggy and glitchy, not the right kind, on phone and desktop.

This is fixed **before any page work**, because every page uses sheets. 27 files open one (listed in §5).

---

## 1. What is wrong, and where (read in code; red test still to be run)

### A. A sheet survives leaving the page (the stuck drawer)

| # | Fact | Where |
|---|---|---|
| A1 | Ionic moves an open inline sheet out of the page and into the app root. Then it is no longer inside the page that opened it. | Ionic 7 inline-modal behaviour (`@ionic/vue` ^7.4.3) |
| A2 | Our dim background (`.g-scrim`) is drawn by hand and **stays inside the page**. | `GModal.vue` (the hand-built backdrop) |
| A3 | Nothing closes an open sheet when the route changes. No route guard, no leave hook. There is also no handling for the app going to the background. | grep: no `onIonViewWillLeave` / `beforeEach` dismiss anywhere |
| A4 | So after a back-swipe or tab change, the **sheet stays on top of the next page**. Its dim layer is hidden with the old page, and its open/closed state is still "open". It looks frozen and doesn't respond like a sheet. | the result of A1 + A2 + A3 |
| A5 | Tapping the dim layer calls `modalController.dismiss()` with **no target**. It closes *whichever* sheet is on top, and fails if that sheet is still animating in. It should close its own sheet. | `GModal.vue`, scrim `@click` |
| A6 | The dim layer turns off only on `willDismiss`. If the dismiss never fires (a gesture cut short, the app sent to the background mid-animation), the layer stays and blocks every tap. | `GModal.vue` `onWillDismiss` |

**Why that reading holds:** A1 is how Ionic ships inline modals (they are presented at the root). A2–A6 were read directly in our code.

**Still to prove:** the exact sequence the owner hit. I will reproduce it first with Playwright:
- open the day sheet
- go back through history, or switch tab, during the open animation
- also hide the page mid-animation

Then assert that the sheet and the dim layer are gone. That test must **fail on today's code** before the fix is written (red first).

### B. The transitions are the wrong kind

| # | Fact | Where |
|---|---|---|
| B1 | The app forces **iOS mode on every device**, so Android phones and desktops get the iPhone push-slide. | `utils/ionicConfig.js`: `mode: "ios"` |
| B2 | The iPhone-only fix (no animation on back-swipe) runs only on iPhone. Android's system back-swipe **plus** Ionic's slide = two animations for one gesture. | `ionicConfig.js`: `isPlatform("iphone")` only |
| B3 | On desktop, a full-width 400ms slide of a 720px column feels like a mobile app in a browser. Desktop apps swap content instantly or with a short fade. | Material 3 motion; Apple HIG (macOS does not slide pages) |
| B4 | Every page paints its own background with **36px blur** (`--g-field-blur`), and the CSS has 21 `backdrop-filter` rules. During a slide, **two** pages of blur animate at once. That is the heaviest thing a browser can repaint, and it shows as stutter. | `glass.css:125`; `glass-components.css` |

---

## 2. The rule we adopt (one rule, whole app)

**Sheets**

1. **Leaving a page closes its sheet first.** A back gesture with a sheet open **closes the sheet and stays on the page**. That is the Android/Material rule ("back dismisses the top surface first"), and iOS apps behave the same way.
2. A sheet closes **itself**, by its own reference, never "whichever is on top".
3. The dim layer is tied to the sheet's **open state**, not to one event. It cannot outlive the sheet.
4. When the app returns from the background, any half-animated sheet is **finished or closed**. It never hangs.

**Transitions**

| Movement | Phone, iOS | Phone, Android | Desktop (≥ 1024px) | Basis |
|---|---|---|---|---|
| Switching tabs | **none** (instant) | **none** | **none** | iOS HIG tab bars: tab switches don't animate. M3 navigation bar: same. |
| Opening a sub-page (e.g. a request) | iOS slide, ~300ms | **fade-through**, ~200ms | **fade**, 150ms or none | Material 3 "fade through / shared axis"; Apple HIG push |
| Going back | reverse of the above | reverse | reverse | same |
| Back-swipe from the screen edge | **no second animation** (the browser already animated it) | same | n/a | extends today's iPhone fix to Android |
| Sheet | slides up from the bottom (kept) | same | centred dialog, fade + slight scale | Apple HIG sheets; M3 dialogs |
| Reduced motion | all of the above become **instant** | | | WCAG 2.3.3 (the app-wide rule already exists) |

Durations stay within NN/g's guidance (100–500ms, shorter for frequent actions).

**Performance during motion**

- While a page transition runs, the **outgoing page's blur is switched off** (one CSS class for the duration). Only one blurred surface animates at a time.
- Test: record a trace (Chrome performance panel through Playwright) of Home → a request → back, at a 4× slower CPU. Pass = no frame over 50ms (the RAIL "response" budget).

---

## 3. What changes (the smallest set that fixes the cause)

| # | Change | File |
|---|---|---|
| F1 | One router guard: if a sheet is open, close it. On a back navigation, **close it and cancel the navigation**. | `src/router/index.js` (next to `traversalQueue.js`, same pattern) |
| F2 | `GModal`: dim layer bound to the open state; close its **own** sheet; close on page-hide and app-hidden | `components/glass/GModal.vue` |
| F3 | Platform-correct animation builder: none for tabs, per-platform for sub-pages, fade on desktop, none after an edge swipe | `utils/ionicConfig.js` |
| F4 | Blur off on the leaving page during a transition | `theme/glass-components.css` + one class toggle |
| F5 | Old `CustomIonModal.vue` users move to `GModal`, so the fix reaches every sheet | the files in §5 still on it |

**Not doing:**
- A new animation library. Ionic's own animation API (`createAnimation`) covers all of it.

---

## 4. Proof

| Check | Test |
|---|---|
| Sheet closes on back / tab switch / app hidden | Playwright, 3 cases, **red on today's code first** |
| Back with a sheet open stays on the page | Playwright: URL unchanged, sheet closed |
| Dim layer never outlives its sheet | Playwright: no `.g-scrim` in the DOM after any of the 3 cases |
| Tab switch has no animation | Playwright: no `ion-page` carries a transform during a tab switch |
| No long frames during a push | Performance trace, CPU ×4, no frame > 50ms |
| Every sheet uses the fixed component | Gate: no raw `ion-modal` outside `GModal.vue` |

---

## 5. Every file that opens a sheet (the full set, checked by the gate)

RequestList · RequestActionSheet · ListView · StrictRejectionDialog · InstallPrompt · Holidays · ExpenseTaxesTable · CheckInPanel · LateCheckoutDialog · RemoteCheckinDialog · Profile · DaySheet · PushNotificationPrompt · HRIssueBoard · TeamRoster · FormView · CustomIonModal · GConfirm · GActionSheet · DesignSpecimen · InvalidEmployee · RemoteApprovals · Login · SopFormSheet · FileUploaderView · ExpensesTable

---

## 6. Cut-off text: app-wide findings

Found in the CSS. Every place where text is cut with "…":

| Where | Verdict |
|---|---|
| Tab bar label | **Keep the guard.** Proven to fit at 320px (the 50.7px label in its 57.6px slot). The "…" only triggers if a translation grows. |
| **Detail-grid values** (`.g-meta__value`, `nowrap` + "…") | **Fix: wrap instead.** A status or a date cut to "Not ma…" is lost meaning. Used in sheets and details. |
| File names | **Keep.** Cutting long file names is the platform norm (iOS Files and Android both do it). The full name is spoken to screen readers and shown on tap. |
| Small grid cell labels (2-line clamp) | **Keep.** It is a guard; every current label fits (measured). |
