CLASS: an Ionic overlay whose own role=dialog wrapper has no name (axe aria-dialog-name, serious): Ionic names it only from the ion-modal host's aria-label.
frontend/src/components/glass/GModal.vue same-root (host gets :aria-label="title"; every GModal sheet in the app)
frontend/src/components/glass/GActionSheet.vue not-affected — ion-action-sheet names itself from its header
frontend/src/views/*: raw <ion-modal> not-affected — grep finds none outside GModal (callers were moved onto it)
