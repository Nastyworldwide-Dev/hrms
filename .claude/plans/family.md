CLASS: the Forgot to check out sheet can show a greyed-out Send with no visible reason, which staff read as a frozen app (#4855)
frontend/src/components/LateCheckoutDialog.vue same-root — empty reason now says "Add a reason to send."; cleared time says "Pick the time you left."
frontend/src/utils/checkinSession.js same-root — a check-in under a minute old has no valid default; returns null instead of a red "now"
frontend/src/components/RemoteCheckinDialog.vue ticket 4855-remote — same disabled-Send pattern not audited here; check in the next pass
frontend/src/components/CheckInPanel.vue not-affected — opens the dialog; picks no time
