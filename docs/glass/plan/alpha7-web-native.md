# Native-feel web on iOS (Safari 18.x / 26 / 27) — capability research for Nadi

Researched 24 Sep 2026. Primary data: MDN browser-compat-data v8.1.2 (published 17 Sep 2026, queried locally from unpkg `@mdn/browser-compat-data/data.json`), caniuse.com, webkit.org release posts.
Safari 27.0 shipped 17 Sep 2026 (https://webkit.org/blog/18325/webkit-features-for-safari-27-0/).
"UNKNOWN" = no primary source found in this pass. Nothing below is guessed.

Key context change (iOS 26): "By default, every website added to the Home Screen opens as a web app" and "there are now zero requirements for 'installability' in Safari." — https://webkit.org/blog/17333/webkit-features-in-safari-26-0/

---

## 1. Dynamic Type (`font: -apple-system-body` etc.)
- **Works on iOS Safari; iOS-only behaviour.** Values: `-apple-system-body`, `-headline`, `-subheadline`, `-caption1/2`, `-footnote`, `short-*`, `tall-body`. They "represent an entire style, including size and weight." Source: https://webkit.org/blog/3709/using-the-system-font-in-web-content/ (Jul 2015).
- Home-screen web apps: WebKit post does not say explicitly. Community reports (Craig Hockenberry) say same WebKit = same behaviour: https://furbo.org/2024/07/04/dynamic-type-on-the-web/ . **Official confirmation for standalone: UNKNOWN — test on device.**
- Gotchas (community): setting `font-size` on the same element after the shorthand breaks the link; macOS Safari also honours it and renders ~13px, so gate with `@supports (font: -apple-system-body)` + iOS check. https://frontendmasters.com/blog/letting-ios-text-size-setting-affect-font-size-on-the-web/
- Recommended pattern: `html { font: -apple-system-body; font-family: <yours>; }` then size everything in `rem`.
- `text-size-adjust`: iOS only as `-webkit-text-size-adjust` (since iOS 1); desktop Safari: no. (MDN BCD `css.properties.text-size-adjust`.) Use `-webkit-text-size-adjust: 100%` to stop landscape auto-inflation.
- Emerging standard `<meta name="text-scale">` — Chrome-only experiment as of early 2026; Safari support UNKNOWN.

## 2. View Transitions
- Same-document (`document.startViewTransition`): **iOS Safari 18.0+** (MDN BCD; caniuse https://caniuse.com/view-transitions; https://webkit.org/blog/15865/webkit-features-in-safari-18-0/).
- Cross-document (`@view-transition { navigation: auto }`): **iOS Safari 18.2+** (https://caniuse.com/cross-document-view-transitions).
- Navigation API (intercept navigations for SPA push/pop): **Safari 26.2** (MDN BCD `api.Navigation.navigate`; https://webkit.org/blog/17640/webkit-features-for-safari-26-2/).
- Caveat: no built-in edge-swipe-back gesture binding; view transitions are not interruptible by finger drag (a native pop is). Gesture-driven back must be hand-built.

## 3. Badging API
- `navigator.setAppBadge()`: **iOS 16.4+, home-screen web apps only**. BCD note: "Badging is supported for web apps saved to the home screen." "Passing 0 … will clear the badge." Also works from Declarative Web Push `app_badge`. Source: https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/ ; MDN BCD `api.Navigator.setAppBadge`.
- Requires notification permission granted (per WebKit 16.4 post context; confirm on device).

## 4. Web Push (iOS 16.4+)
- **Home Screen web apps only**; permission request must be "in response to direct user interaction." Integrates with Focus; manifest `id` (16.4+) used to sync Focus across devices. https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/
- `PushManager.subscribe`: iOS 16.4, note "supported in web apps saved to the home screen" (MDN BCD).
- **Notification actions (buttons): NOT supported** (BCD `options_actions_parameter`, `Notification.actions` = false). Also not supported: `requireInteraction`, `image`, `badge` (icon), `silent`, `tag`, `renotify`, `vibrate`; `icon` "can be set, but has no effect" (BCD).
  - Implication: approve/reject-from-notification is impossible; tap must deep-link into the app.
- **Silent push: not allowed** — WebKit requires `userVisibleOnly: true`; failing to show a notification historically penalised the subscription (https://webkit.org/blog/16535/meet-declarative-web-push/).

## 13. Declarative Web Push
- **iOS/iPadOS 18.4+, for web apps added to the Home Screen** (https://webkit.org/blog/16574/webkit-features-in-safari-18-4/). macOS 15.5.
- JSON payload with `web_push: 8030`, `notification: { title (required, non-empty), body, navigate (required URL), lang, dir, silent, app_badge }`. No actions array.
- No service worker needed to display; SW can still replace it, fallback shown if SW fails. No silent-push penalty. Backwards compatible (old browsers handle via JS). https://webkit.org/blog/16535/meet-declarative-web-push/
- Best fit for Nadi: reliable delivery + badge count in one payload.

## 5. Passkeys / WebAuthn (Face ID)
- WebAuthn `navigator.credentials.get/create` with platform authenticator: iOS Safari 13+ (BCD `api.PublicKeyCredential`).
- Conditional mediation (autofill UI: `isConditionalMediationAvailable`): **Safari 16** (BCD).
- Conditional **create** (automatic passkey upgrade after password sign-in): **Safari 18.0** (https://webkit.org/blog/15865/webkit-features-in-safari-18-0/).
- `parseCreationOptionsFromJSON`/`toJSON`: 18.4. Signal API (`signalUnknownCredential` etc.): **26.0** (BCD; https://webkit.org/blog/17333/). PRF extension: 18.0; PRF improvements + CTAP PIN protocol 2: 26.4 (https://webkit.org/blog/17862/webkit-features-for-safari-26-4/).
- Standalone web app specifics: UNKNOWN (no WebKit statement found). Needs device test; passkeys are bound to RP ID (domain), so the Frappe site domain is the RP.

## 6. Web Share / Share Target
- `navigator.share`: iOS 12.2+; `canShare` (files): iOS 14+ (BCD; https://caniuse.com/web-share). Needs user gesture.
- **Web Share Target (`share_target` in manifest): NOT supported** on iOS (BCD `manifests.webapp.share_target` = false, tracking https://webkit.org/b/194593). Nadi cannot appear in the iOS share sheet.

## 7. Haptics
- **Vibration API: not supported on any iOS Safari version** (https://caniuse.com/vibration; BCD `Navigator.vibrate` = false).
- **`<input type="checkbox" switch>`**: Safari 17.4+ (https://webkit.org/blog/15054/an-html-switch-control/). Native iOS switch look, ARIA `switch` role, honours "On/Off Labels". `::thumb`/`::track` not shipped.
- **iOS 18 "adds haptic feedback for `<input type=checkbox switch>`"** (https://webkit.org/blog/15865/webkit-features-in-safari-18-0/). This is the only documented web haptic on iOS.
- Community hack (programmatically clicking a hidden `<label>` for a switch to trigger the haptic) exists; not an Apple-sanctioned API — treat as fragile / UNKNOWN longevity.

## 8. Wake Lock, Geolocation, Camera, Permissions
- Screen Wake Lock: iOS 16.4 in Safari; **in Home Screen web apps only since 18.4** ("now also works in Home Screen Web Apps on iOS and iPadOS 18.4" — https://webkit.org/blog/16574/). BCD notes 16.4–18.3 "Does not work in standalone Home Screen Web Apps" (webkit.org/b/254545).
- Geolocation: supported (watchPosition since iOS ≤3). Accuracy is whatever Core Location returns; user can switch off "Precise Location" per-app/Safari, giving a coarse fix (km-scale). No web API to request precise. Standalone-specific accuracy statement: UNKNOWN. (Matches the known "coarse fix" defect in project memory.)
- getUserMedia camera: iOS 11+ (BCD). **Standalone permission persistence is buggy**: re-prompts on route/hash changes — https://bugs.webkit.org/show_bug.cgi?id=215884 , Apple forum 2025 https://developer.apple.com/forums/thread/788518 . Mitigation: keep one page/stream alive, avoid hash routing changes while camera is in use, request once per session.
- Permissions API `query`: iOS 16 (camera, geolocation, microphone), notifications 16.4, push 17, screen-wake-lock 16.4 (BCD). `Permissions.request` not supported.

## 9. Offline / Background
- **Background Sync: not supported** (https://caniuse.com/background-sync; BCD SyncManager false, webkit.org/b/182565). **Periodic Background Sync: not supported.** Queue offline check-ins in IndexedDB and flush on next app open / `online` event.
- Service worker + Cache API: supported (SW inspection improvements in 26.0).
- Storage quota (Safari 17+): browser app origin up to 60% of disk; "other apps" 15%; standalone web app "has the same origin quota and overall quota as when it is opened in a browser app." `navigator.storage.persist()` granted "based on heuristics like whether the website is opened as a Home Screen Web App." LRU eviction per origin; persistent-mode origins excluded. https://webkit.org/blog/14403/updates-to-storage-policy/
- 7-day script-writable storage cap (ITP): Home Screen web apps "have their own counter of days of use"; "We do not expect the first-party in such a web application to have its website data deleted." https://webkit.org/blog/10218/full-third-party-cookie-blocking-and-more/
- Home-screen web apps have storage separate from Safari (sessions/cookies not shared) — widely documented; primary source for iOS 26: UNKNOWN in this pass.

## 10. Visual platform bits
| Feature | iOS status | Source |
|---|---|---|
| `backdrop-filter` | unprefixed 18.0; `-webkit-` since 9 | BCD; https://webkit.org/blog/15865/ |
| backdrop-filter performance | No WebKit perf guidance found — UNKNOWN; practice: few, small, non-scrolling blurred layers | — |
| `prefers-reduced-transparency` | **Not supported** (incl. 27.x) — webkit.org/b/175497 | BCD; caniuse |
| `prefers-contrast` | 14.5 (`custom` parse 18.0) | BCD |
| `prefers-reduced-motion` | 10.3 | BCD |
| `color-scheme` | 13 | BCD |
| `theme-color` meta | 15; **from iOS 26 only used for installed web apps** | BCD note |
| `apple-mobile-web-app-status-bar-style` | `default` / `black` / `black-translucent` (content under status bar). Apple archive doc; `black-translucent` flagged deprecated by Web Inspector but still used | https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariHTMLRef/Articles/MetaTags.html |
| `viewport-fit=cover` + `env(safe-area-inset-*)` | 11+ | BCD; https://web.dev/learn/pwa/app-design |
| `interactive-widget` | **Not supported** (incl. 27.x) | BCD; caniuse |
| VirtualKeyboard API | Not supported (webkit.org/b/230225) | BCD |
| `overscroll-behavior` | 16+, **partial**: no effect on containers without scrollable overflow (webkit.org/b/243452) | BCD |
| `display-mode: standalone` | 12.2; quirk: with manifest `display: standalone`, `standalone` is false and `fullscreen` true (webkit.org/b/264218) — detect with both, or `navigator.standalone` | BCD |
| Manifest | display standalone/browser 11.3, scope 11.3, id 16.4, theme_color 15; **not**: shortcuts, orientation, background_color, display_override, protocol_handlers, share_target | BCD |
| `-webkit-tap-highlight-color`, `-webkit-touch-callout`, `-webkit-user-select` | supported | BCD |
| `field-sizing: content` | 26.2 | BCD; webkit 26.2 post |
| `text-wrap: balance` 17.5, `pretty` 26 | | BCD |
| `corner-shape: squircle` | Not supported | BCD |

## 11. Scroll-driven animations
- `animation-timeline` with `scroll()` / `view()`, `animation-range`: **iOS Safari 26.0+** (BCD; https://caniuse.com/mdn-css_properties_animation-timeline; https://webkit.org/blog/17333/).
- **Threaded (off-main-thread) since 26.4** (https://webkit.org/blog/17862/). Good for collapsing large title / shrinking tab bar without JS.
- Needs `@supports (animation-timeline: scroll())` fallback for iOS ≤18.

## 12. Dialog / Popover / Anchor positioning
- `<dialog>`: 15.4. `closedby` attribute: **not supported** (BCD).
- Popover API: iOS 17.0–18.2 partial (tap-outside does not light-dismiss, webkit.org/b/267688); **full from 18.3** (BCD; caniuse).
- Invoker commands (`command`/`commandfor` buttons): **26.2** (BCD; https://webkit.org/blog/17640/).
- `:open` pseudo-class: 26.5 (BCD).
- Anchor positioning (`anchor-name`, `position-area`, `position-try`): **26.0** (caniuse marks 26.x "partial", full in 27.0 with transform-aware anchoring and `position-anchor` default changed to `normal`). https://webkit.org/blog/17333/ ; https://webkit.org/blog/18325/
- `interpolate-size` (animate to `height: auto`): not supported (BCD).

## 14. Engineering guidance (big companies / research)
- **Google web.dev Core Web Vitals**: LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1, measured at the 75th percentile of page loads. https://web.dev/articles/vitals
- **Google web.dev "App design" (Learn PWA)**: system font stack; `user-select: none` on UI controls only, never content; `overscroll-behavior-y: contain` to kill pull-to-refresh; `viewport-fit=cover` + safe-area insets for critical content; `display-mode` media query; solid `theme-color`; honour `prefers-color-scheme` and `prefers-reduced-motion`; `accent-color` for controls. https://web.dev/learn/pwa/app-design
- **Microsoft Edge PWA docs**: HTTPS, manifest (`display: standalone`), service worker for cache-first offline "Faster / More reliable / Network-independent". https://learn.microsoft.com/en-us/microsoft-edge/progressive-web-apps/how-to/ (a dedicated Microsoft "app-like UX" page URL 404'd — UNKNOWN current location).
- **Apple**: current developer.apple.com "Configuring web applications" URL 404'd; only the archived Safari Web Content Guide / Safari HTML Reference (status-bar meta, apple-touch-icon) was reachable. Modern Apple guidance for web apps = WebKit blog posts above. Human Interface Guidelines apply to the design (44 pt targets etc.) but were not re-fetched in this pass.
- **Nielsen Norman**: 0.1 s "limit for having the user feel that the system is reacting instantaneously"; 1.0 s "limit for the user's flow of thought to stay uninterrupted"; 10 s "limit for keeping the user's attention focused." https://www.nngroup.com/articles/response-times-3-important-limits/
- Airbnb / Shopify / Stripe content guidelines: not researched (tool budget) — UNKNOWN.

---

## Summary table

| Capability | iOS home-screen support | Since | Source |
|---|---|---|---|
| Dynamic Type `-apple-system-*` | Yes in Safari; standalone not officially stated (community: yes) | iOS 7-era, doc 2015 | webkit.org/blog/3709 ; furbo.org 2024 |
| `-webkit-text-size-adjust` | Yes (prefixed) | iOS 1 | MDN BCD |
| View Transitions same-doc | Yes | 18.0 | caniuse; webkit 18.0 |
| View Transitions cross-doc | Yes | 18.2 | caniuse |
| Navigation API | Yes | 26.2 | webkit 26.2 |
| Badging | Yes, home screen only | 16.4 | webkit 13878; BCD |
| Web Push | Yes, home screen only, gesture-gated permission | 16.4 | webkit 13878 |
| Notification action buttons | **No** | — | BCD |
| Silent push | **No** (userVisibleOnly) | — | webkit 16535 |
| Declarative Web Push | Yes, home screen | 18.4 | webkit 16574 / 16535 |
| Passkeys + autofill (conditional get) | Yes (standalone: UNKNOWN, test) | 16 | BCD |
| Passkey auto-upgrade (conditional create) | Yes | 18.0 | webkit 18.0 |
| WebAuthn Signal API | Yes | 26.0 | webkit 26.0; BCD |
| Web Share | Yes | 12.2 (files 14) | BCD; caniuse |
| Web Share Target | **No** | — | BCD (webkit.org/b/194593) |
| Vibration API | **No** | — | caniuse |
| `<input switch>` | Yes | 17.4 | webkit 15054 |
| Switch haptic | Yes | 18.0 | webkit 18.0 |
| Screen Wake Lock | Yes in standalone | 18.4 (Safari tab 16.4) | webkit 18.4; BCD |
| Geolocation | Yes; precision user-controlled | ≤3 | BCD |
| Camera getUserMedia | Yes, but permission re-prompts in standalone | 11 (standalone 13.4 era) | webkit bug 215884 |
| Background Sync / Periodic | **No** | — | caniuse; BCD |
| Storage persist() | Yes; granted more readily for home-screen apps | 15.2 / policy 17 | webkit 14403 |
| 7-day ITP wipe | Home-screen apps exempt in practice (own day counter) | 13.4 | webkit 10218 |
| backdrop-filter | Yes | 18 (prefixed 9) | BCD |
| prefers-reduced-transparency | **No** (even 27) | — | BCD; caniuse |
| prefers-contrast / reduced-motion / color-scheme | Yes | 14.5 / 10.3 / 13 | BCD |
| theme-color | Yes; iOS 26 uses it only for installed apps | 15 | BCD |
| status-bar-style meta | Yes (3 values) | legacy | Apple archive |
| safe-area env() + viewport-fit | Yes | 11 | BCD |
| interactive-widget | **No** | — | BCD; caniuse |
| overscroll-behavior | Partial | 16 | BCD |
| Scroll-driven animations | Yes (threaded 26.4) | 26.0 | caniuse; webkit 26.4 |
| `<dialog>` | Yes (`closedby` no) | 15.4 | BCD |
| Popover | Yes (full) | 18.3 | BCD |
| command/commandfor | Yes | 26.2 | BCD; webkit 26.2 |
| Anchor positioning | Partial 26.x, full 27.0 | 26.0 | caniuse; webkit 27 |
| field-sizing | Yes | 26.2 | BCD |

## What a top Apple-platform engineer would use (10 lines)
1. `font: -apple-system-body` on `html` (gated to iOS) + `rem` everywhere, so iOS Text Size scales the app like a native one.
2. Declarative Web Push (18.4+) with `navigate` deep links + `app_badge`; no action buttons exist, so the tap must land on the exact approval screen.
3. `navigator.setAppBadge()` synced to the unread/pending-approval count on every app open.
4. Passkeys: conditional-mediation autofill sign-in + conditional-create upgrade → "log in with Face ID", no passwords.
5. `<input type=checkbox switch>` for every toggle — native look, VoiceOver role, and the only real web haptic on iOS.
6. Navigation API (26.2) + same-document View Transitions for push/pop; hand-built edge-swipe back.
7. Scroll-driven animations (`animation-timeline: scroll()`) for large-title collapse and tab-bar minimise, `@supports` fallback for iOS 18.
8. Popover + `command`/`commandfor` + anchor positioning for menus/sheets; `<dialog>` for modals; manual light-dismiss (no `closedby`).
9. Offline queue in IndexedDB flushed on open/`online` (no Background Sync); request `storage.persist()`; keep one camera stream alive to dodge standalone re-prompts; wake lock during selfie capture.
10. Budget: INP ≤ 200 ms, LCP ≤ 2.5 s, CLS ≤ 0.1 (p75), every tap answered in ≤ 100 ms; blur sparingly with `@supports` + solid fallback (no `prefers-reduced-transparency` on iOS).
