CLASS: a scrollable area inside an Ionic sheet modal that is not an ion-content, so Ionic's sheet gesture takes every drag in it as "move the sheet"
frontend/src/components/glass/GModal.vue same-root — content now inside ion-content.g-sheet__content; every sheet in the app renders through it
frontend/src/theme/glass-components.css:.g-sheet same-root — column layout; the scroll moves from .g-sheet to the ion-content
frontend/src/components/glass/GActionSheet.vue not-affected — renders inside GModal
