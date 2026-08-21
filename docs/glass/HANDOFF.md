# HANDOFF
prompt:   7.2 (auth field reversal + Login rebuild, spec v1.7)
status:   done
commit:   1c5662e1c on nz-glass
files:    frontend/src/views/Login.vue (rebuilt to §12)
          frontend/src/views/{ForgotPassword,ChangePassword,InvalidEmployee}.vue
          frontend/src/components/glass/GProviderButton.vue
          frontend/src/theme/glass-components.css (.g-auth)
          design/gates/surfaces.mjs (declared-exception mechanism)
          docs/glass/spec/…v1.1.md → v1.7 (§0, §20.8)
verify:   cd frontend && yarn gates && yarn build
flags:    LOGIN IS 2/6 WITH THE FIELD ON — GLogoWell + GProviderButton. Nothing app-wide
          exceeds §15
          THE 4.2 REASONING WAS WRONG, as ruled: the field is three static CSS gradients,
          no session, no data, no fetch. 5.7's "auth surfaces must be solid" followed only
          from that premise and is withdrawn. GProviderButton is glass again
          GATE NOT WEAKENED: a glass surface under v-for still FAILS by default. A list
          bounded by ADMIN CONFIG (not user data) may declare itself with a greppable
          "glass-surfaces: bounded — reason". Login's SSO list declares it; an undeclared
          loop still exits 1, verified by probe
          TRANSLATIONS WRITTEN to verify-bench/fresh.local (Translation doctype, en):
            "Login to Frappe HR"          → "Sign in to NSTY People"
            "Employee self-service portal"→ "Attendance, leave, claims and payslips in one place"
            "Frappe HR · Mobile & Tablet" → "NSTY Holding · People & Culture"
          These are DATA, not code — they do not travel with the repo and must be created
          on the target site too
          SSO LABEL IS DATA: "Office 365" is Social Login Key → provider_name. Change it in
          Desk (Social Login Key list → the record → Provider Name), not in code.
          GProviderButton renders "Sign in with {provider_name}" and names no vendor
next:     §18 sign-off checklist — device work, not code
