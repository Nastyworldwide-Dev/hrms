# HANDOFF
prompt:   2.3
status:   done
commit:   f4b06b790 on nz-glass
files:    frontend/src/components/glass/ (10 new + translate.js helper)
          frontend/src/theme/glass-components.css
          frontend/src/views/DesignSpecimen.vue
verify:   cd frontend && yarn gates && yarn build
flags:    §20.7 list INCOMPLETE — #24 App header differs at lg: today (avatar hidden, kicker shown); preserved, needs spec amendment
          header material unspecified — built non-glass, §15.2 counts no header in its per-screen arithmetic
          §4.2 has no 13px/15px/23px/10.5px steps (§10.2 #16, #21, #23, #18) — nearest token used, needs a §4.2 ruling
          clock seconds ink@.55 = 4.26 light: valid only while decorative + aria-hidden
next:     phase 2 prompt 4 — remaining components; then phase 4 wires the shell
