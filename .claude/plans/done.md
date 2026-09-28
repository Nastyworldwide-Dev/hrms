GOAL: the update bar never appears on a real phone with nothing deployed.
DONE WHEN: main.js registers the worker at an address that is the same every launch for the same push settings (utils/workerURL.js: sorted keys; a failed relay fetch reuses the last good settings).
CHECK: node --test frontend/src/utils/__tests__/workerURL.test.js; live on fresh.local with push_relay_server_url set and a relay stub that reorders keys and fails every 3rd launch: HEAD bar on 5/6 launches, fix 0/6.
