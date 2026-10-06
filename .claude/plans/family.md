CLASS: a part of a screen that shows nothing when its data fails to load (alpha.37 L1 list): a blank reads as "there is nothing", not "it did not load".
frontend/src/components/RequestTimeline.vue same-root (ResourceError in place)
frontend/src/components/ExpensesTable.vue, ExpenseTaxesTable.vue same-root (ResourceError in place)
frontend/src/components/MustReadNotice.vue same-root (a failed body: ResourceError, footer kept; a failed notice LIST: logged and nothing shown, because the notice cannot be dismissed and must never block the app)
