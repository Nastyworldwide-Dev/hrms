# HANDOFF
prompt:   1.2
status:   done
commit:   7989d0862 on nz-glass
files:    design/build-tokens.mjs
          frontend/package.json
          frontend/src/theme/glass.css
          frontend/src/theme/glass.tailwind.cjs
          frontend/src/theme/glass.variables.css
verify:   cd frontend && yarn tokens && git diff --exit-code src/theme
flags:    rgba tokens (accent-glow, glass, glass-fallback, rim, rim-hi, rim-lo, hair, icon-bg, sheen) take no Tailwind opacity modifier
          pad-* two-value tokens not in Tailwind spacing; motion `property` + `one-shot` not emitted; --ion-tab-bar-background-focused←icon-bg is a judgment map
next:     prompt 1.3 wires glass.css + fragment into tailwind.config.js/main.js
