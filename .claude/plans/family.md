CLASS: holding back a message for every case when only some screens say it themselves: (1) a refused read was silent on any screen without its own "You can't open this."; (2) a must-read whose text failed to load could still be confirmed, because its end marker was on screen.
frontend/src/utils/loudRequest.js same-root (a signed-in refusal: toast "You can't open this." unless the screen drew it — data-no-access — checked a frame later; never starts the repeat window)
frontend/src/components/FormView.vue, ResourceError.vue same-root (mark data-no-access where they draw the sentence)
frontend/src/utils/mustRead.js + components/MustReadNotice.vue same-root (failed text -> "Load it to confirm"; onConfirm retries the load, never records)
frontend/src/components/ExpensesTable.vue ticket alpha.39 — addButtonDisabled ignores claimTypesResource.error (review suggestion)
