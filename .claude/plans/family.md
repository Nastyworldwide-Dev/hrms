CLASS: a disabled button whose reason is on screen but not tied to the button, so a screen reader hears a dimmed control with no reason
frontend/src/components/LateCheckoutDialog.vue same-root — Send now aria-describedby the "Add a reason to send." hint
frontend/src/components/glass/GButton.vue not-affected — single-root button; attrs fall through
frontend/src/components/glass/GCheckbox.vue not-affected — already takes describedBy for its disabled reason
frontend/src/components/RemoteCheckinDialog.vue ticket 4855-remote — same disabled-Send pattern; audit in the next pass
