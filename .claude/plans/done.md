GOAL: a form row never cuts its value mid-letter and never shows a number field's spin buttons.
DONE WHEN: labels keep their text width; a picker reserves its chevron and ellipsises; number fields in forms draw no spinner. Issue "Required" whole, OT Hours clean.
CHECK: node --test frontend/src/theme/__tests__/row-control-fit.test.js; page-audit 402+1280, sheet + ios consistency all 0
