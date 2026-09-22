# HANDOFF
prompt:   redundant title / page-scroll items from the original bug report
status:   done (investigated, no defect found — no code change)
commit:   none (docs only, see below)
files:    .claude/plans/progress.md
verify:   none — no code changed
flags:    Redundant title: no literal duplicate reproduces on mobile PWA.
          Checked ListView+BaseLayout overlap (none), in-body heading dupes
          (0/11 BaseLayout views), SideNav vs header (real but desktop-only,
          hidden on phone, and standard nav pattern anyway). Scroll/pagination:
          Home is bounded (RequestPanel caps at 10); real list screens already
          paginate (ListView.vue page_length:50 + infinite scroll). Earlier
          NEXT line's framing of the title bug was wrong — corrected in ledger.
next:     nothing actionable left from the original report. Owner's word on
          FOUR (mockup folder, Mockup 4 sign-off, visual/IA contract,
          --g-glass-fill) still blocks further 2.0 work.
