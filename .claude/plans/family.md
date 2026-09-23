CLASS: glass (backdrop-filter) on the content layer instead of chrome
frontend/src/theme/glass-components.css:.g-glass same-root (solid fallback fill)
frontend/src/theme/glass-components.css:.g-glass-ghost same-root
frontend/src/theme/glass-components.css:.g-modal same-root (sheet becomes glass)
frontend/src/theme/glass-components.css:toast same-root
frontend/src/theme/glass-components.css:ion-tab-bar.g-tabbar not-affected — chrome, already correct
frontend/src/theme/glass-components.css:.g-sidenav not-affected — chrome, already correct
frontend/src/theme/glass-components.css:.g-header not-affected — nothing scrolls under it (ion-header outside a non-fullscreen ion-content)
frontend/src/components/BottomTabs.vue same-root (scroll-edge fade)
design/gates surfaces counter ticket alpha5-gate-surfaces — counts .g-glass class, not blur; still passes
