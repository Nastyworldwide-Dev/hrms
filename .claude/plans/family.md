CLASS: two nested dialogs with the same name (Ionic's named wrapper + our inner role=dialog), announced twice; and a hard-coded English accessible name in a translated app.
frontend/src/components/glass/GModal.vue same-root (inner .g-sheet is no longer a dialog; Ionic's wrapper is the one, named)
frontend/src/components/MustReadNotice.vue same-root (same)
frontend/patches/frappe-ui+0.1.105.patch same-root (toast Close goes through __() like GModal's Close)
frontend/e2e/audit-crawl.spec.js, alpha6-audit.mjs, alpha6-journey.mjs not-affected — select ion-modal as well as [role=dialog]
