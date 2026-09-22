# HANDOFF
prompt:   2.0 revamp — phases A, B, C and D
status:   done, ready to deploy
commit:   cd8144e7c on nz-glass (20 commits, all pushed)
files:    hrms/api/{announcements,needs_you,requests_summary,calendar,now}.py
          hrms/hr/doctype/hr_announcement{,_read}/ (new)
          hrms/patches/v16_0/install_announcement_doctypes.py
          design/gates/{scale,motion}.mjs (new), lint/contrast/run extended
          design/tokens.json — 4pt grid, 1.2 type ramp, icon + control scales
          frontend/src/components/{NowBar,Announcements,DaySheet,RequestBalances}.vue
          frontend/src/views/announcements/ (new)
verify:   cd frontend && yarn test && yarn gates && yarn build
flags:    763/763 tests green. 7 static gates green. a11y/visual/coherence still
          SKIP — they need a served site with AUDIT_PW, as they have for six
          releases; the board says so rather than reporting OK.
          114 visual baselines still owed, and now 228 (light theme is real).
next:     Deploy. On the phone: Home's top line states your shift and your
          running hours; announcements appear once HR posts one; Calendar tiles
          carry dots and a day opens a sheet; Requests shows your balances;
          Score says when your cycle opens.
