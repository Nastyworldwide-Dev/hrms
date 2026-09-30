GOAL: the Team roster "Assign shift" button shows its words, and a supervisor's own row reads "You".
DONE WHEN: GButton gets :label; is_self row reads You; test red before, green after; browser shows "Assign shift".
CHECK: node --test frontend/src/views/team/__tests__/team-roster-assign.test.js
