<!--
  GPage — the page scaffold every screen goes through (spec §3.2, §15.3).

  It owns the page SHELL only: the ion-page element and the layering that keeps
  content above the light field. It does NOT own ion-content or the header —
  each view still writes those.

  THE FIELD MOVED OUT IN 8.18. It used to be mounted here, one per page, which
  meant three simultaneous fields during a push because Ionic keeps three pages
  alive. App.vue now owns a single instance. §3.2's original reason for putting
  it inside the page — surviving Ionic's backdrop-root — was re-verified before
  the move and no longer binds: nothing between the shell and a glass surface
  carries `contain: paint`, a transform or a filter.

  §15.3: the field is not a glass surface and costs nothing against the budget.

  Props:
  Slot: default — the view's own ion-header / ion-content, unchanged
-->
<template>
	<ion-page class="g-page">
		<!-- The field is back inside the page (Track B), paired with the opaque
		     .g-page ground — see the invariant note on .g-lightfield. One field
		     per LIVE page exists again, but only the top page's is visible:
		     the ground occludes the rest, which is the whole point. -->
		<GLightField />
		<slot />
	</ion-page>
</template>

<script setup>
import { computed, provide } from "vue"
import { useRoute } from "vue-router"
import { IonPage } from "@ionic/vue"
import GLightField from "@/components/glass/GLightField.vue"

import { TAB_ITEMS } from "@/data/navItems"

defineProps({})

// THE BACK RULE LIVES HERE (§12, v1.11). It used to be a per-screen decision:
// 26 screens had a back control, 12 did not, and the split was whatever each
// author chose — four pushed screens simply lacked one. GPage knows whether it
// is a tab root, so it decides once and every header consumes the answer.
const route = useRoute()
const isTabRoot = computed(() => TAB_ITEMS.some((t) => t.route === route.path))
provide(
	"gShowBack",
	computed(() => !isTabRoot.value)
)
</script>
