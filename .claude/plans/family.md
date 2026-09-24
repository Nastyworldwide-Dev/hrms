CLASS: an iOS-only overlay pinned over every route (install hint in a frappe-ui Popover, lime fill, contrast 1.18)

Instance: WebKit audit 25 Sep (plan §11, 0.10): with an iPhone UA, "Install Nadi" covered the bottom of every page, forms included.

Sites:
- frontend/src/components/InstallPrompt.vue iOS Popover — same-root (removed; iOS path now InstallHint on Home)
- frontend/src/components/InstallPrompt.vue GModal (Android/desktop beforeinstallprompt) — not-affected: a dismissible sheet, only fires where the browser offers install, keeps its 30-day cooldown
- frontend/src/utils/installPromptMemory.js — same-root (showIosInstallHint: iPhone, not installed, not closed in 30 days)
- frontend/src/views/Home.vue — same-root (the one place the hint renders)
- frontend/src/components/UpdatePrompt.vue — not-affected: shown only when a new build is waiting, not per platform

Locked: installPromptMemory.test.js (+2). Verified in WebKit with iPhone UA: row on Home at top, absent on the leave form, gone after Close + reload.
