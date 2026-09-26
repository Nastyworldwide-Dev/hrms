GOAL: first paint on a slow phone drops from 10.4 s by shipping only what the first screen needs
DONE WHEN: main bundle 1.27 MB -> 654 KB; FCP 10.4 s -> 6.3 s on 4x CPU / 150 ms / 1.6 Mbps; toast icons still draw; all tests green
CHECK: cd frontend && yarn test && yarn build
