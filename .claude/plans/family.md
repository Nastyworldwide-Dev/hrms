CLASS: an Ionic overlay whose own role=dialog wrapper has no name (axe aria-dialog-name): Ionic names it only from the ion-modal host's aria-label.
frontend/src/components/glass/GModal.vue same-root (fixed in the previous commit)
frontend/src/components/MustReadNotice.vue same-root (the one other raw ion-modal; its name sat on the inner div only)
frontend/src/components/glass/__tests__/sheet-dialog-has-a-name.test.js same-root (invariant: every raw ion-modal in src carries :aria-label)
