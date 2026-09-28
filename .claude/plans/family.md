CLASS: the service worker's URL built from data that changes between launches (push settings order; relay fetch success), so the browser sees a new worker every launch
frontend/src/main.js:registerServiceWorker same-root — workerURL() with sorted settings and the last good copy on relay failure
frontend/src/components/UpdatePrompt.vue not-affected — already offers only a worker waiting behind an active one, per build id (b2f020a62)
frontend/public/sw.js not-affected — still reads ?config= the same way (test: the worker can read the settings back)
