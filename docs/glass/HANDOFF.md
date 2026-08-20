# HANDOFF
prompt:   4.3 (tab bar, side nav, More)
status:   done
commit:   71e1de252 on nz-glass
files:    frontend/src/data/navItems.js (TAB_ITEMS 6 → 5)
          frontend/src/components/BottomTabs.vue (floating pill)
          frontend/src/components/SideNav.vue (glass, two groups per §20.2)
          frontend/src/views/More.vue (GListPanel + GListRow)
          frontend/src/theme/glass-components.css (tab bar + side nav)
          design/gates/usage.mjs (direct-import rule tightened)
verify:   cd frontend && yarn gates && yarn build
flags:    FLOATING PILL WORKS WITHOUT REPLACING ion-tab-bar — the host is light DOM, so
          position/inset/radius/backdrop-filter are ours; only the interior needed
          custom properties. Per-tab navigation stacks untouched
          BRIEF WAS WRONG TWICE: TAB_ITEMS had 6 entries not 8; and §13.1's PAY has no
          route — no salary-slip screen exists, building one is out of scope (§1).
          Expenses takes the 4th slot. DECISION 2 + the PAY substitution both pending P&C
          Remote Approvals had NO entry in any nav surface — URL-only. Now behind More per §13.1
          usage gate fired on comment prose for the 3rd time in this project; direct-import
          now matches real import/@import only, verified against both forms
next:     phase 5 — the 41 screens. Usage gate should flip to --strict at its start
