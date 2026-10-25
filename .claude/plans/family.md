CLASS: a live-region message that outlives the visible toast it mirrors (stale screen-reader news)
frontend/src/components/glass/announce.js same-root — fixed: cleared after CLEAR_AFTER_MS (toast lifetime); all gToast + announce() callers route through it
frontend/src/components/NeedsYou.vue, Approvals.vue local role=status lines not-affected — they describe the current page state and change with it
frontend/src/components/glass/toast.js:56 same-root — gToast is the caller whose words outlived the toast; the clear in announce() covers it
