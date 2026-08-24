# HANDOFF
prompt:   persona/residue UX audit; rebrand Frappe HR -> Nadi, both themes
status:   done
commit:   5854aec26 on nz-glass
files:    frontend/{vite.config.js,index.html,ionic.config.json,package.json}
          frontend/src/utils/productName.js (+ test)
          frontend/src/components/{SideNav,Login,BaseLayout,GAppHeader,GLogoWell,InstallPrompt}.vue
          hrms/hooks.py, hrms/desktop_icon/*.json (+ rename patch), hrms/{install,uninstall}.py
          roster/src/components/NavBar.vue, roster/src/icons/NadiLogo.vue (new)
          hrms/public/{images,manifest}/* (favicon/icons/30 splash screens, regenerated)
verify:   set -a; . ./.env; set +a; node design/gates/run.mjs   (8/8 clean, run twice)
flags:    kept --g-brand #C8FF00 for CSS/vector surfaces, not the asset's literal
          #CEFA05 (near-identical, avoids re-baselining the whole product); the
          logo file itself had one baked corner - user chose sharp-square icons.
next:     roster/ has zero dark mode (separate Tailwind app, no token bridge) -
          the one persona-facing theme gap left. bench migrate needed per instance.
