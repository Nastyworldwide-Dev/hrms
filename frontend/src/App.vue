<template>
	<ion-app>
		<!-- ONE light field for the whole app (8.18). It used to live inside
		     GPage, so every routed page carried its own — and during a push
		     Ionic keeps three pages alive at once, which meant THREE fields
		     painting simultaneously, all opaque. That is the overlap a human
		     saw mid-transition.

		     §3.2 put it inside the page to survive Ionic's backdrop-root, and
		     that constraint was verified again before moving it: walking from a
		     glass surface to the shell, every ancestor carries
		     `contain: size layout style` — no `paint` — and the only backdrop
		     root created during a push is a page at opacity 0, which is
		     invisible regardless. Nothing cuts the blur. -->
		<GLightField />
		<ion-router-outlet id="main-content" />
		<Toasts />

		<InstallPrompt />
	</ion-app>
</template>

<script setup>
import { onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

import { Toasts } from "frappe-ui"

import GLightField from "@/components/glass/GLightField.vue"
import InstallPrompt from "@/components/InstallPrompt.vue"
import { showNotification } from "@/utils/pushNotifications"

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
