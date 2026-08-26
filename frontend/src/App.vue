<template>
	<ion-app>
		<!-- The field lives inside GPage again (Track B). 8.18 moved it here to
		     stop three per-page fields painting through each other — but that
		     required transparent pages, and transparent pages turned every push
		     into a double exposure of two screens. The invariant both attempts
		     missed: a routed page must be opaque. .g-page now owns an opaque
		     ground, so per-page fields cannot stack visually — the top page
		     occludes the rest. See .g-lightfield in glass-components.css. -->
		<ion-router-outlet id="main-content" />
		<Toasts />

		<InstallPrompt />
	</ion-app>
</template>

<script setup>
import { onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

import { Toasts } from "frappe-ui"

import InstallPrompt from "@/components/InstallPrompt.vue"
import { showNotification } from "@/utils/pushNotifications"

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
