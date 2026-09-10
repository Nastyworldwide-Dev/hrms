# HANDOFF
prompt:   PWA location stall (mainland China) + attendance follow-ups
status:   done
commit:   231392219 on nz-glass
files:    frontend/src/components/CheckInPanel.vue
          frontend/src/components/__tests__/CheckInPanel.location.test.js
          .claude/plans/current-plan.md
verify:   cd frontend && node --experimental-test-module-mocks --test "src/components/__tests__/*.test.js" "tests/*.test.mjs"
flags:    Tampin root cause FOUND (Shift Location > Shift Rules had a 7PM-3.30AM
          row; the daily sync creates assignments from it). HR removed the row.
          The rule-vs-manual bug in hrms/hr/shift_rules.py:123 is NOT fixed:
          "manual wins" returns before closing rule-created rows, so both stay
          active. That is next.
next:     Nabil deploys 231392219; then fix shift_rules manual-vs-rule overlap
