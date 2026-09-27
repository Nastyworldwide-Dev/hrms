GOAL: a decided request's files are shown, not changed: no "Add a file", no remove, no empty file band.
DONE WHEN: FormView passes isFormReadOnly to FileUploaderView; decided leave HR-LAP-2026-00045 shows no Add a file and no empty band.
CHECK: node --test frontend/src/components/__tests__/decided-attachments.test.js; WebKit decided leave: addFile false
