# HANDOFF
prompt:   5.7 (batches 6–9 — SOP, team, settings, auth)
status:   done; phase 5 screens complete, some shared internals remain
commit:   a23f7495f on nz-glass
files:    frontend/src/components/{PdfInlineViewer,PushNotificationPrompt}.vue
          frontend/src/components/glass/GProviderButton.vue (new)
          frontend/src/views/Login.vue (3 dialogs + SSO)
          frontend/src/views/{ForgotPassword,ChangePassword}.vue
          frontend/src/views/{Notifications,AppSettings,RemoteApprovals}.vue
          frontend/src/views/{sop/SopList,sop/SopDetail,team/TeamDashboard}.vue
verify:   cd frontend && yarn gates && yarn build
flags:    COUNTS — everything 0–1/6 plus chrome. Login 1/6 with one sheet set. Nothing
          anywhere in the app is above 5/6
          NO ANATOMY WRITTEN. Every screen in these four batches follows a settled
          pattern, so per the 4.4 ruling the pattern is the anatomy. §12 unchanged
          :field="false" CONFIRMED, and it has a consequence worth stating: those screens
          have NO light field, so any glass on them is grey fog (§3's opening line).
          Auth surfaces must be SOLID. GProviderButton is solid for exactly this reason
          THE GATES CAUGHT THIS: a raw g-glass-ghost class in Login and a v-for of glass
          provider buttons both failed. Both were mine, both were real
          SSO is provider-agnostic — GProviderButton reads name and mark from the server
          record. The mark renders unmodified: no filter, tint, mask or radius. Wording is
          "Sign in with {name}". No vendor is named anywhere in the code
          BOTH REMAINING §10.3 ITEMS BUILT: PDF viewer (solid per §6.3, skeleton not
          spinner) and push prompt (GModal). §10.3's list is now complete
          STILL UNSTYLED: the three expense tables (ExpensesTable, ExpenseTaxesTable,
          ExpenseAdvancesTable) → GDataTable, Holidays, RequestList's EmptyState, and
          KPI's KRA rows → GKraPanel. All shared internals, none screen-level
next:     sweep the shared internals above, then §18's sign-off checklist
