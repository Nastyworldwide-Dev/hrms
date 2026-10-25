CLASS: an Ionic modal whose can-dismiss is false refuses the close that is-open=false asks for, leaving an empty modal over the app (blank screen)
frontend/src/components/MustReadNotice.vue same-root — fixed: can-dismiss is a function, closable once no notice is left (confirm of the last notice, or Remind me later on it)
frontend/src/components/glass/GModal.vue:52 (Approvals.vue:367 dismissible while phase !== 'working') not-affected — the sheet leaves 'working' for 'result' before it closes, and sheet=null makes dismissible true
