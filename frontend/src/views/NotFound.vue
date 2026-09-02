<!--
  NotFound — the catch-all (8.13).

  The router had no catch-all at all, so ANY unknown URL rendered a completely
  blank page: no message, no way back, nothing to tell you whether the app had
  crashed or the link was wrong. The 8.x audit found it by way of /design, which
  is `import.meta.env.DEV` only and therefore absent from production builds —
  a route the app legitimately does not have, presenting exactly like a fatal
  error.

  §11.3: plain language, no system vocabulary. It does not say 404.
-->
<template>
	<GPage>
		<ion-content :fullscreen="true">
			<div class="flex min-h-full w-full flex-col items-center justify-center px-4">
				<GEmptyState
					:title="__('That page isn\'t here')"
					:body="__('The link may be out of date, or the page may have moved.')"
				/>
				<div class="mt-6 w-full max-w-content-column-lg mx-auto">
					<GButton :label="__('Go to Home')" @click="router.replace({ name: 'Home' })" />
				</div>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import { inject } from "vue"
import { useRouter } from "vue-router"
import { IonContent } from "@ionic/vue"

import GPage from "@/components/glass/GPage.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GButton from "@/components/glass/GButton.vue"

const __ = inject("$translate")
const router = useRouter()
</script>
