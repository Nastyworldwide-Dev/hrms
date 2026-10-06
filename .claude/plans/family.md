CLASS: a refresh that fans out per event. Every employee's punch reaches every open app through list_update; each used to reload two reads and now reloads four (3a54590cd), so a burst (HR fixing many punches, a shift starting) times the number of open apps could hit the server in the tens of thousands within seconds (review of 3a54590cd, worst case 50 x 200).
frontend/src/components/CheckInPanel.vue:useListUpdate same-root (fixed here: the realtime path waits a second and runs once per burst)
frontend/src/components/CheckInPanel.vue:refreshAfterPunch same-root — the person's OWN punch still calls it directly, immediate, never through the debounce
frontend/src/composables/realtime.js:useListUpdate ticket realtime-fanout — the helper has no debounce or per-employee filter for any caller (ListView, RequestPanel register several); checked here only for CheckInPanel
frontend/src/components/ListView.vue not-affected — its list_update handler reloads one list, unchanged
