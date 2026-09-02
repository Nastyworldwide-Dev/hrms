# HANDOFF
prompt:   Frontend closure pass
status:   3 gaps closed w/ rendered proof; 1 verification blocked by env
commit:   ae099e447 on nz-glass
closed:   (1) Adaptive balance grid — count-driven: odd last tile spans full
          width on mobile, desktop uses exactly `count` cols (cap 5). 1-5+ clean,
          no orphan. Verified: 3 types -> full-width-3rd mobile / 3-across
          desktop. (b27be1e15)
          (2) Desktop centering — 7 content views left-pinned the column
          (2 already centered = the pattern); added mx-auto so all center in the
          post-sidebar space. Verified: Home/Leaves balanced ~250px/side.
          (a88760e21)
          (3) Install-prompt lifecycle — gated surfacing on a signed-in session;
          no longer shows over the login form. Verified: login renders clean.
          (ae099e447)
role-qa:  Employee-side role-gating verified clean — Team shows a proper
          "Nothing waiting on you" empty state, More drops role-gated rows to a
          shorter list; NO holes/malformed layouts. PRIVILEGED HR/Approver render
          BLOCKED: fresh.local has only Administrator with HR roles + no manager
          employees, and provisioning a role user was denied by the permission
          classifier. Could not certify what I could not render.
a11y:     tab targets 44px; icon buttons labeled ("Notifications, 30 unread");
          keyboard focus visible (box-shadow ring); prefers-reduced-motion and
          reduced-transparency both wired. Representative, not exhaustive.
states:   empty (Team/NotFound) + loading skeleton (GBalanceGrid) + error
          (ResourceError) + focus/selected verified; full matrix not exhaustive.
verify:   yarn build OK; eslint clean; installPromptMemory tests pass.
verdict:  FRONTEND NOT READY — the three concrete defects are fixed and proven,
          but the mandated privileged HR/Approver rendered QA could not be
          completed (no role user; provisioning denied). Unblock: provision an
          HR + an Approver test user (each with an Employee) and this closes.
