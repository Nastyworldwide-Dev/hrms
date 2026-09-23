CLASS: the dim area behind a sheet lived inside the page the sheet makes inert, so a tap on it did nothing.

Call sites: frontend/src/components/glass/GModal.vue scrim — same-root, fixed (utils/sheetScrim places it before the presented ion-modal). GActionSheet and other sheets render through GModal — same-root. Back-while-opening race in sheetGuard/GModal — ticket P0-3b (pre-existing, reproduced on HEAD 3/5 runs), next commit.
