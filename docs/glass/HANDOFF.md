# HANDOFF
prompt:   2.2 (correction — §6.3 overrides §10.1)
status:   done
commit:   81be95f73 on nz-glass
files:    design/tokens.json (+ regenerated glass.css, glass.tailwind.cjs)
          frontend/src/theme/glass-components.css
          frontend/src/components/glass/GProgressRing.vue
          frontend/src/components/glass/GBalanceCard.vue
          docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md (§6.3, §10.1 #6, #9)
verify:   cd frontend && yarn tokens && yarn gates && yarn build
flags:    --track-solid = #ECEDEF / #313133, the exact composite of icon-bg over glass — appearance unchanged, value no longer shifts with the backdrop
          brand arc vs track measures 1.01 light: pre-existing, explicitly permitted by §2.4 (balance bar fill named, label always present)
next:     KRA bars (§10.2 #16) must use --track-solid when built — §6.3 names them
