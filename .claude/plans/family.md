CLASS: code needed by one screen or a later moment sat in everyone's first download
frontend/src/components/WorkflowActionSheet.vue — same-root (ion-action-sheet -> GActionSheet; also passed the translated label as the workflow action)
frontend/src/views/Profile.vue + utils/dialogs.js — same-root (Ionic alert -> gToast; dialogs.js removed)
frontend/src/router/index.js closeSheetsOnLeave — same-root (only modals exist now; action-sheet/popover controllers dropped)
frontend/src/{Home,Requests,Approvals,announcements/List}.vue, ListView.vue GPullRefresh — same-root (async component)
frontend/src/utils/frappe-push-notification.js — same-root (firebase loaded on first use)
frontend/src/utils/__tests__/frappe-push-notification.test.js — same-root (VM seam for the lazy import)
