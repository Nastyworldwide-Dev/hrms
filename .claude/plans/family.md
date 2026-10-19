CLASS: the keyboard focus ring hidden from someone who IS on the keyboard (WCAG 2.4.7), after the pointer-ring fix
frontend/src/utils/focusModality.js same-root — Enter/Space/letters on a control now count as keyboard; nothing hidden before the first tap
frontend/src/theme/glass-components.css same-root — text inputs, textareas, selects, contenteditable keep their ring after a tap
frontend/src/components/glass/GModal.vue not-affected — Chromium focuses the ion-modal host on Enter-open (no ring rule on it); data-input is "keyboard" there, so nothing is hidden by this change
