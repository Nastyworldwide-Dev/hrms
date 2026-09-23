<!--
  GPage — the page scaffold every screen goes through (spec §3.2, §15.3).

  It owns the page SHELL only: the ion-page element and its opaque ground.
  It does NOT own ion-content or the header — each view still writes those.

  No background blobs (owner ruling, 23 Sep 2026): the light field that used to
  mount here was decoration with no job and doubled the blurred layers on every
  page push.

  Props:
  Slot: default — the view's own ion-header / ion-content, unchanged
-->
<template>
	<ion-page class="g-page">
		<slot />
	</ion-page>
</template>

<script setup>
import { computed, provide } from "vue"
import { useRoute } from "vue-router"
import { IonPage } from "@ionic/vue"

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
