# HANDOFF
prompt:   Check-in stuck on "Location unavailable" indoors / on mobile data (owner, 29 Oct 2026)
status:   done
commit:   alpha.72 on nz-glass (fix 9085c0c4c, review fix 8727cfb15)
files:    frontend/src/components/CheckInPanel.vue
frontend/src/components/__tests__/CheckInPanel.location.test.js
verify:   deploy (migrate only if alpha.71 not live); check in indoors where it failed; location appears within ~10 s
flags:    no device test here; wrong-phone-clock case left as is (owner set it aside)
next:     affected staff retry from the same indoor spot
