# HANDOFF
prompt:   2.0 complete — eight slices, plus pre-2.0 and the attendance repair
commit:   9db488f45 on nz-glass (69 commits today, all pushed)
status:   done
files:    frontend/src/data/navItems.js
          frontend/src/views/Requests.vue (new)
          frontend/src/components/NeedsYou.vue (new)
          frontend/src/components/FormView.vue
          frontend/src/views/{leave,expense_claim}/Form.vue
          frontend/src/views/{attendance,ot}/*
          frontend/src/views/RemoteApprovals.vue
          design/tokens.json
verify:   cd frontend && yarn test && yarn gates && yarn build
flags:    618 tests / 614 pass — the same 4 fail at HEAD and predate today.
          Gates: lint 234 new-0, contrast 56/0, surfaces 47 screens 0 over.
          NOTHING rendered: no site was reachable, so every check is
          stub/source-level. Three defects on 22 Sep came from exactly that.
          OWED: 1440 baselines, and the 2026-09-09 measurements (tabH 0 on all
          36 screens, marked stale in its own data).
next:     Deploy. On the phone check: the Reload bar clears the tab bar and its
          x closes it; pull-to-refresh does not print through the date; the
          leave-type search does not zoom; the tab bar reads Home Calendar
          Requests Score More.
