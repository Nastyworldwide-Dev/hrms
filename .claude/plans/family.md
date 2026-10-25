CLASS: start-up work tied to the first successful read, so a retry that succeeds leaves the screen half set up
frontend/src/components/FormView.vue onMounted/reloadDoc same-root — fixed: setUpForm() run on mount and by Try again when the first open never set up
frontend/src/components/FormView.vue workflowApplied/reload callers of reloadDoc not-affected — they run after a successful set-up (isSetUp true), so reloadDoc behaves as before
