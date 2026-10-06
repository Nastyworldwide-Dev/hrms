# HANDOFF
prompt:   alpha.37 "Clear Screens" (Stage 4 screens standard + session refactor)
status:   done
commit:   0db6c24c6 on nz-glass (tag v2.0.0-alpha.37, GitHub Release created)
files:    frontend/src/components/ResourceError.vue
          frontend/src/components/glass/GListRow.vue (+7 request rows)
          frontend/src/components/glass/GModal.vue, MustReadNotice.vue
          frontend/patches/frappe-ui+0.1.105.patch (toast Close)
          frontend/src/utils/personalCache.js (sessionEnded)
          design/a11y-baseline.json (empty: 0 serious on 76 screen-themes)
          docs/glass/audit/2026-10-06-shift-supervisor-desk.md
verify:   after deploy: open someone else's record -> "You can't open this."; long name rows stay one line
flags:    a second "Something didn't load" toast can follow the no-access sentence (alpha.38)
next:     owner deploys alpha.35-37 together on Frappe Cloud
