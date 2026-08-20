# HANDOFF
prompt:   3.1 (analysis only)
status:   done
commit:   17dc38a80 on nz-glass
files:    docs/glass/phase3-inventory.md
          design/gates/usage.mjs
          design/usage-baseline.json
          design/gates/run.mjs
verify:   cd frontend && yarn gates    (usage gate now runs as gate 5)
flags:    §16.2 WRONG on both counts — rounded-* touches 4 app files not 103; real radius risk is 106 utilities in 47 frappe-ui components. Arbitrary values are 403 not 303
          variables.css CANNOT be deleted as-is: 40 of its 47 hexes are Ionic --ion-color-* ramps with no Glass equivalent — needs a ruling before 3.4
          modernist.css deletion breaks text-ink-*/bg-ground app-wide (tailwind colours resolve via --m-*); Archivo link must go WITH the fontFamily.sans repoint, not before
          sequence amended: radius restore split into its own 3.5 commit
next:     ruling on §6.1 (Ionic ramps), then 3.2 promote/absorb — touches no view
