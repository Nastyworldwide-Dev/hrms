# HANDOFF
prompt:   4.2 (scaffold, header, safe area, lg: check)
status:   done
commit:   7078f8536 on nz-glass
files:    frontend/src/components/glass/GPage.vue (new scaffold)
          25 views migrated ion-page → GPage
          frontend/src/components/BaseLayout.vue (GPage + GAppHeader)
          frontend/index.html (viewport meta)
          frontend/src/theme/glass-components.css (layering, lg: geometry)
          design/gates/contrast.mjs (lg: §3.3 assertion)
verify:   cd frontend && yarn gates && yarn build
flags:    lg: ASSERTION CAUGHT A 4.1 BUG — scaling blob size with vw but not the offsets
          marched centres into the column (dark ink-muted 1.08 at 1440px). Origin:size ratio
          now held; 54/54 pass, and at lg no blob reaches the column at all
          4 auth/error screens take :field="false" — Login, ForgotPassword, ChangePassword,
          InvalidEmployee render before a session and have no glass to sit behind
          2 routers (FormShell, TabbedView) keep a bare ion-page: §3.2 needs the field in the
          CHILD page Ionic transforms, not the parent that hosts the outlet
          SAFE AREA: meta now parses as 3 directives (was 2, viewport-fit swallowed) and env()
          resolves. Non-zero insets CANNOT be verified without an iOS device — human must check
          DECISION 3 OPEN: removing maximum-scale restores iOS focus-zoom on sub-16px inputs.
          Recorded, not decided; no input font sizes changed
next:     4.3 tab bar + side nav (both untouched here)
