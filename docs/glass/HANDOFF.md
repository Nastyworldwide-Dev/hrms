# HANDOFF
prompt:   5.1 (phase 5 batch 1 — Home)
status:   done, with one anatomy conflict flagged
commit:   9440b341a on nz-glass
files:    frontend/src/components/glass/GConfirm.vue (new)
          frontend/src/components/FormView.vue, FileUploaderView.vue,
          InstallPrompt.vue, views/InvalidEmployee.vue (Dialog → GModal/GConfirm)
          frontend/src/components/QuickLinks.vue, PendingApprovalsBanner.vue,
          RequestPanel.vue
          design/gates/surfaces.mjs (strict by default)
verify:   cd frontend && yarn gates && yarn build
flags:    HOME = 3/6 (GBanner + GListPanel + tab bar). Nothing over budget anywhere
          §12's Home anatomy lists a BALANCE GRID (2 cards). The shipped Home has no
          balance data and no such call — adding it is a content change, not a re-skin.
          NOT BUILT. Needs a ruling: amend §12, or add it as a feature in its own prompt
          §12 also omits RequestPanel, which Home does have. Anatomy vs reality differs
          in both directions
          4 of 5 Dialog swaps done. Login's 3 DEFERRED — they hold forms with validation,
          not confirmations; batch 9 owns them
          Home's primary opens the check-in sheet and does not await the server, so pending
          would be misleading there. The button that DOES punch (sheet Confirm) already
          carries :pending from 3.3b — §11.4 is satisfied on the right button
          surfaces gate counts modal contents even when closed (conservative). Form screens
          read 4/6 largely because GConfirm's ghost cancel is a glass surface
next:     batch 2 (Check-in) — needs the 3 geofence dialogs, still unbuilt
