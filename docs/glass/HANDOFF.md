# HANDOFF
prompt:   theme switching back, update popup removed, regression + desktop check
status:   done
commit:   fb6dc5745 on nz-glass (tag v2.0.0-alpha.23)
files:    frontend/src/views/Profile.vue
          frontend/src/data/theme.js
          frontend/index.html
          frontend/src/data/swRegistration.js
          frontend/public/sw.js
          frontend/src/App.vue
verify:   You -> Appearance -> Dark stays dark after reload; no "A new version is ready" bar
flags:    theme picker reverses alpha.12 ruling R4 (owner 30 Sep); iOS gate 9/9 0 findings incl. desktop
next:     alpha.24 larger text; ticket .claude/plans/ticket-one-my-team-rule.md
