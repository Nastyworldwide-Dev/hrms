# HANDOFF
prompt:   diagnose the Nadi desktop-icon regression; fold it into the phase 9 plan
status:   done (planning only - no code changed)
commit:   9c7efcb16 on nz-glass
files:    docs/glass/plan/HR_Glass_Phase_9_Work_Order.md (new §0.5 Phase 0, order, matrix)
          docs/glass/HANDOFF.md
verify:   bench --site verifica-live execute frappe.client.get_list --kwargs
          '{"doctype":"Desktop Icon","filters":{"parent_icon":"Frappe HR"},"fields":["name"]}'
flags:    PHASE 0 OUTRANKS ALL OF PHASE 9 - it is live breakage on verifica-live.
          Root cause: standard-doc import is timestamp-gated (import_file.py:141).
          The rebrand changed parent_icon in 9 desktop_icon fixtures WITHOUT
          bumping `modified`, so it never landed; then the rename patch deleted
          "Frappe HR" with force=True, orphaning them. 11 files carry this defect
          - 2 are workspace fixes from 17 Aug that also never reached production.
          CI cannot catch it: patch.yml restores v14, which has no Desktop Icons.
          The uncommitted desktop_launcher.js CANNOT fix it - same failing guard.
next:     0.3 guard, then 0.2 timestamps, 0.1 repair patch, 0.5 test. Then 9.2c.
