CLASS: an Ionic modal's role=dialog wrapper is named only from the host aria-label present at first load; a later or changed title never reaches it
frontend/src/components/glass/GModal.vue same-root — fixed: nameSheet on every will-present (all 41 GModal sheets)
frontend/src/components/MustReadNotice.vue same-root — fixed: nameSheet on will-present and on each new notice title
other raw ion-modal users not-affected — sheet-dialog-has-a-name.test.js asserts there are none besides these two
