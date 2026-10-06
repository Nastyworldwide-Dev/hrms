CLASS: one wording for three different situations: "Failed to fetch" is the phone offline OR the server unreachable while online, and "your form is kept" is only true where a form is open; "Nothing was sent" can be false when the connection drops after the request left.
frontend/src/utils/loudRequest.js:firstMessage same-root (network failure -> "No connection." / "Could not reach the server." by navigator.onLine; used by all 27 readers, none promises a form)
frontend/src/utils/loudRequest.js:saveFailedSentence same-root (form-save sites only: "... so it may not have been sent. What you typed is still here.")
frontend/src/utils/loudRequest.js:makeLoudRequest same-root (generic toast held back only when the phone is offline; an unreachable server while online still toasts — no banner would)
frontend/src/components/FormView.vue (create, update, submit) same-root (save sites use saveFailedSentence; delete keeps firstMessage)
frontend/src/views/sop/SopFormSheet.vue (save) same-root
14 non-form readers (leave/Form read, HRIssueBoard load, commonUtils PDF, CheckInPanel selfie, RequestActionSheet, composables, workflow, check-in dialogs) not-affected — get the plain network words, no form promise
