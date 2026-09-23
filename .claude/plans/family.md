CLASS: a fallback timer left running after the event it guards arrived.

Call sites: frontend/src/components/UpdatePrompt.vue reload() — same-root, fixed. GPullRefresh capTimer — not-affected (complete() on a closed refresher is a no-op, verified in review of e522bada8).
