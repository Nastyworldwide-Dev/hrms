<!--
  GPage — the page scaffold every screen goes through (spec §3.2, §15.3).

  It owns the page SHELL only: the ion-page element, the light field mounted
  inside it, and the layering that keeps content above the field. It does NOT
  own the header or the content, which stay in the slot exactly as each view
  wrote them. That boundary is deliberate — unifying the shell makes the field
  and safe area consistent across all 38 pages, while a scaffold that also
  owned content would have to reconcile every view's ion-content props
  (`fullscreen`, `ion-no-padding`, `scroll-y`) and could not be swapped in
  without changing behaviour.

  §3.2 is the whole reason this exists as a component rather than a global:
  Ionic animates transform and opacity on .ion-page, making it a backdrop root.
  A field mounted anywhere above the page is invisible to every backdrop-filter
  inside it after the first navigation. Mounting it here, once, means no view
  can get that wrong.

  §15.3: the field is not a glass surface and costs nothing against the budget.

  Props:
    field  boolean, default true — set false for pages that deliberately carry
           no light field (see the auth screens in phase 4.2's HANDOFF)
  Slot: default — the view's own ion-header / ion-content, unchanged
-->
<template>
	<ion-page class="g-page">
		<GLightField v-if="field" />
		<slot />
	</ion-page>
</template>

<script setup>
import { IonPage } from "@ionic/vue"
import GLightField from "./GLightField.vue"

defineProps({
	field: { type: Boolean, default: true },
})
</script>
