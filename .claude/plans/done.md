GOAL: every Nadi release has its tag and a GitHub Release; one script makes both
DONE WHEN: release-tags test passes; scripts/release.sh --backfill lists a release per v2.0.0 tag
CHECK: node --test design/gates/release-tags.test.mjs && gh release list --limit 20
