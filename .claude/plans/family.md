CLASS: an event handler registered inside a try block that can fail first, so it is sometimes never registered
frontend/public/sw.js:notificationclick same-root — moved outside the Firebase try; waitUntil; reuses an open window
frontend/public/sw.js:onBackgroundMessage not-affected — needs Firebase, correctly inside the try
frontend/src/utils/pushNotifications.js:showNotification not-affected — foreground notifications go through the same worker handler
frontend/src/utils/safeHtml.js:69 not-affected — "url()" is a CSS function in a comment, not the worker's local `url` variable
hrms/public/js/hierarchy_chart/hierarchy_chart_desktop.js:536 not-affected — SVG marker url(#...) string
hrms/public/js/hierarchy_chart/hierarchy_chart_desktop.js:537 not-affected — SVG marker url(#...) string
hrms/public/js/hierarchy_chart/hierarchy_chart_desktop.js:540 not-affected — SVG marker url(#...) string
hrms/public/js/hierarchy_chart/hierarchy_chart_desktop.js:541 not-affected — SVG marker url(#...) string
hrms/public/js/hierarchy_chart/hierarchy_chart_mobile.js:381 not-affected — SVG marker url(#...) string
hrms/public/js/hierarchy_chart/hierarchy_chart_mobile.js:382 not-affected — SVG marker url(#...) string
hrms/public/js/hierarchy_chart/hierarchy_chart_mobile.js:496 not-affected — CSS background-image url(), unrelated
