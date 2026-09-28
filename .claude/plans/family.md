CLASS: the update offer identified a "new build" by the service worker's URL, which stopped naming builds when the worker moved to one fixed URL (/hrms/sw.js, alpha.12) and was registered twice under two URLs
frontend/src/components/UpdatePrompt.vue same-root — no second registration; asks the waiting build for its id
frontend/src/main.js:register same-root — shares its one registration (data/swRegistration.js)
frontend/public/sw.js same-root — answers GET_BUILD_ID from its own precache
frontend/src/utils/updatePromptMemory.js:waitingBuildId same-root — removed; it read a __WB_REVISION__ that /hrms/sw.js never carries
frontend/src/components/InstallPrompt* not-affected — install prompt uses its own cooldown memory, no worker identity
