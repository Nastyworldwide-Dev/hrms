# HANDOFF
prompt:   2.4 (phase 2 complete)
status:   done
commit:   cdaaa3c4c on nz-glass
files:    frontend/src/components/glass/ (10 new: GModal, GActionSheet, GSearchBar,
          GAvatar, GDataTable, GFileUpload, GLinkPicker, GDatePicker,
          GPullRefresh + toast.js) — 37 components total
          frontend/src/theme/glass-components.css
          frontend/src/views/DesignSpecimen.vue
          design/tokens.json (scrim token) + regenerated theme files
verify:   cd frontend && yarn gates && yarn build
flags:    frappe-ui installed is 0.1.105, NOT 0.1.278 — Combobox absent, so GLinkPicker wraps Autocomplete; adopting it means DECISION 6
          ion-refresher inner icons are shadow DOM with no published vars — spinner switched off (§11.2 wants that), indicator replaced in light DOM
          new scrim token (backdrop) not in the spec token table; toast + Autocomplete skins couple to frappe-ui internal markup
          §10.3 remaining unbuilt: geofence dialogs (3), PDF viewer, push-notification prompt
next:     phase 3 — retire Modernist; phase 4 — shell + desktop
