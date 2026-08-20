# HANDOFF
prompt:   3.2
status:   done
commit:   a26a2342f on nz-glass
files:    docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md (now v1.3: §0, §16.2, §16.3)
          design/tokens.json (layer group, content-column-lg, sheet-max-height)
          design/build-tokens.mjs (emits layer + layout; zIndex + maxWidth in fragment)
          frontend/tailwind.config.js (textUnderlineOffset, maxHeight — NOT borderRadius)
          frontend/src/theme/glass-components.css (GModal absorbs the sheet ceiling)
          14 files under frontend/src/components/ (name-for-value swaps only)
verify:   cd frontend && yarn tokens && yarn gates && yarn build
flags:    lint 479 → 452 (-27), baseline ratcheted down to 64 files
          3.1 inventory CORRECTED: border-t-[3px] is the Modernist sheet top edge → GModal, not GBanner; under Glass it does not survive at all
          layer tokens preserve the current inverted order (sticky 1000 paints over overlay 100) — promoted, not re-ordered
          content-column had an invalid CSS value ("100% - 30px"); wrapped in calc() so the layout group could be emitted
next:     3.3 replace call sites + .m-* → G* (type first, then chips); 3.4 delete Modernist; 3.5 remap radius
