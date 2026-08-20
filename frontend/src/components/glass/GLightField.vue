<!--
  GLightField — the light field (spec §3). Three static blurred radial
  gradients beneath the UI layer. Glass requires colour behind it or it renders
  as grey fog.

  §3.1 STATIC. No drift animation. Continuous animation of blurred layers
  behind backdrop-filter is the most expensive thing this design can do to a
  mid-range Android, and §7 classes the mockup's drift as presentation material.

  §3.2 THIS MUST RENDER INSIDE THE PAGE'S STACKING CONTEXT — never on ion-app,
  body, or a fixed wrapper outside the page. Chromium's backdrop-filter only
  filters its own isolation group, and Ionic's ios-mode transitions animate
  transform AND opacity on .ion-page, which makes that element a backdrop root.
  A globally-rendered field looks correct on first paint and turns to grey fog
  during and after every navigation — it would pass a screenshot test and fail
  in use. Mount it as a child of <ion-page>; see BaseLayout.vue.

  §15 accounting: the field is NOT a glass surface and costs nothing against
  the six-surface budget. It is what the glass surfaces blur; it carries no
  backdrop-filter of its own. Confirmed reading, not an assumption.

  §20.4 desktop: fixed to the viewport rather than the content column, so the
  field spans the full width while the column stays left-aligned. Blob sizes
  scale with the viewport; the opacity token is unchanged.

  Props: none. Geometry and colour come from the field tokens so the §3.3
  placement check in design/gates/contrast.mjs reads the same source the CSS
  does — see that gate for the measured overlap.
-->
<template>
	<div class="g-field" aria-hidden="true">
		<span class="g-field__blob g-field__blob--a" />
		<span class="g-field__blob g-field__blob--b" />
		<span class="g-field__blob g-field__blob--c" />
	</div>
</template>
