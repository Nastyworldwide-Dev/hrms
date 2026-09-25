GOAL: zoom off (owner ruling 25 Sep) and list pages stop scrolling 28px past their content
DONE WHEN: scroll-and-shift-audit shows 0 real "fits but scrolls"; input-zoom + list-one-scroller tests green
CHECK: yarn --cwd frontend test; node frontend/e2e/scroll-and-shift-audit.mjs
