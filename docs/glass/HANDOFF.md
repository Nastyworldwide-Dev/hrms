# HANDOFF
prompt:   5.5 (batch 5 — shared ListView / FormView)
status:   done
commit:   5d33d9cd1 on nz-glass
files:    frontend/src/components/ListView.vue (7 lists)
          frontend/src/components/FormView.vue + FormField.vue (8 forms)
          frontend/src/theme/glass-components.css
          docs/glass/spec/…v1.1.md (§11.1 + six lists)
verify:   cd frontend && yarn gates && yarn build
flags:    COUNTS — all 7 lists 1/6 (one GListPanel each, no tab bar: they are pushed
          routes). All 8 forms 0/6 with four sheet sets of 1. Nothing near the limit
          IT IS 15 SCREENS, NOT 14 — ListView backs 7 lists, FormView 8 forms
          (IssueForm has no list twin). issues/IssueList and ot/ReplacementLeave use
          NEITHER shared component; they are bespoke and still unstyled
          NO GSEARCHBAR: ListView's filtering is a filter SHEET, not a text search.
          There is no search input to restyle and adding one is new behaviour
          §11.1 covered 3 of the 9 doctypes ListView serves. Six more written in its
          voice and recorded back into §11.1; the copy lives in ONE map in ListView
          FormField still renders Link/Select through frappe-ui Autocomplete and Date
          through its DatePicker — GLinkPicker and GDatePicker WRAP those same
          components, so swapping adds a layer without changing what renders. Left as
          is deliberately; revisit if the wrappers gain behaviour
          TextEditor untouched — no Glass equivalent exists and §10.3 does not name one
next:     batch 4 (KPI + Issues), which also picks up the two bespoke list screens
