CLASS: an `@ionXxx=` template binding on a raw Ionic web component, which Vue hyphenates to a listener name ("ion-xxx") that the component never dispatches (it dispatches the literal camelCase "ionXxx")
frontend/src/components/glass/GPullRefresh.vue:39 same-root — ionStart/ionRefresh rebound via addEventListener
frontend/src/components/ListView.vue:37 same-root — ionScroll rebound via addEventListener
frontend/src/components/ListView.vue:39 not-affected — @refresh="handleRefresh" is GPullRefresh's own Vue emit, not an Ionic DOM event; unaffected by this class
