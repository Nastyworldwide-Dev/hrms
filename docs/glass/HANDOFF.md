# HANDOFF
prompt:   Nadi everyday-use completeness & reliability
status:   done (9 functional PWA fixes; no visual redesign)
commit:   ccd0a1fb2 on nz-glass (21a1307c3..ccd0a1fb2)
files:    RemoteApprovals/HRContacts/ReplacementLeave/HRIssueBoard (error-vs-empty)
          Profile/AppSettings/ChangePassword + above (goBackOrHome)
          ListView (dead New button), Login (error feedback),
          ShiftRequestForm (approver race), FormView (inline error blocks submit),
          Profile (detail-sheet load race)
verify:   cd frontend && yarn build; node --test tests/*.test.mjs (61/63;
          the 2 fails are the pre-existing frappe-ui call-error-handling patch test)
fixed:    approvers no longer see a failed load as an empty queue; Back never
          strands on a cold push deep link; no dead New on read-only lists; a
          failed sign-in shows a message; shift-request approver survives the
          fetch race; an inline validation error blocks submit everywhere;
          profile detail sheet survives an early tap
recorded: one-tap approve/reject in RequestActionSheet has no confirm (RemoteApprovals
          DOES confirm) — a UX-policy call, left as a recommendation not a change
next:     product decision on approval confirmation; then the visual pass
