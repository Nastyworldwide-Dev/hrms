# HANDOFF
prompt:   2.3 amendments (spec v1.2)
status:   done
commit:   615419a4f on nz-glass
files:    docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md
verify:   grep -n '^### v1.2\|^### 15.3\|scale is closed' docs/glass/spec/HR_Frappe_Glass_Spec_v1.1.md
flags:    10.5px was ALREADY a scale step (Caption/Eyebrow) — my 2.3 flag was wrong; #18 needed a token name, not a new size
          ruling applied to SIZE only; weights in §10 entries stand (KRA score stays 12.5/800)
          §20.7 count corrected 24→23; filename kept at _v1.1.md, §0 carries the version
          GCalendar still hardcodes 10.5px instead of --g-type-caption-size — one-line follow-up, docs-only prompt
next:     phase 2 prompt 4 — remaining components
