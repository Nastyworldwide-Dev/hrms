CLASS: a refusal shown as a glitch to retry: after "You can't open this." the request seam also toasted "Something didn't load. Try again", and a refused DOCUMENT read in the form shell said "Could not open ... check your connection and try again" with a Try again that cannot work.
frontend/src/utils/loudRequest.js same-root (no generic toast for a no-access refusal from a signed-in person; isNoAccess shared with ResourceError)
frontend/src/components/FormView.vue same-root (a refused document read: "You can't open this." with Back; other failures keep Try again)
frontend/src/views/helpdesk/TicketDetail.vue same-root (a refused reply had only the seam's toast as its voice: it now toasts "Reply not sent" itself; helpdesk.reply in SILENT_ENDPOINTS)
frontend/src/components/RequestActionSheet.vue, composables/index.js, workflow.js not-affected — their onError toasts the server's reason
frontend/src/views/Notifications.vue mark-as-read ticket alpha.39 — no onError; a refused mark-as-read is now silent (it changes nothing the person sees)
