# HANDOFF
prompt:   ensure ALL config + data carried by sync (half-filled employees), repeatable
status:   done (audit shipped) — awaiting a run against Verifica to produce the gap list
commit:   2157cdc04 on nz-glass
files:    hrms/sync/parity.py — 3 read-only checks: field_completeness, link_coverage,
          source_customizations (source-vs-hub, HR-scoped, whitelisted HR/System Manager)
          hrms/sync/test_parity.py — pure tests for _diff_field_fill (sync-gap vs source-gap)
verify:   bench --site <site> execute hrms.sync.parity.field_completeness --args '["<instance>"]'
          also link_coverage(<instance>) and source_customizations(<instance>); all read-only
flags:    field_completeness splits blanks: empty-but-filled-on-source = SYNC bug (I fix),
          empty-on-both = SOURCE gap (HR fills). No writes; run before cutover.
next:     run the 3 checks on Verifica; rule the gap list; if sync-fidelity gaps appear I fix
          the sync to carry those fields, then re-sync
