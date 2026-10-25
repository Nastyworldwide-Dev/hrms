CLASS: a descendant selector :not(.x) [attr] matches through any ancestor without .x (body), so it cannot exclude an .x subtree
frontend/src/utils/requestFailure.js noAccessDrawn same-root — fixed: each card checked with closest(".ion-page-hidden")
frontend/src/utils/loudRequest.js:34 same-root — wires the reporter
frontend/src/components/glass/GModal.vue:145 not-affected — its :not() sits on the .ion-page itself, which is the correct form
