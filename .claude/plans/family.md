CLASS: notification state refreshed only by a socket event that a sleeping phone misses
frontend/src/data/notifications.js same-root — refreshNotifications on the shared gap hook
frontend/src/App.vue same-root — foreground push calls refreshNotifications
frontend/src/components/RequestPanel.vue not-affected — already reloads on the gap hook
frontend/src/views/Notifications.vue not-affected — reads the same shared resources
