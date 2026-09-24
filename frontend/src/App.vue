<template>
	<ion-app>
		<!-- FIRST, and in flow: the bar pushes every screen down while it shows
		     rather than painting over GAppHeader's back control, which is not
		     fixed and expects nothing above it. -->
		<!-- WCAG 2.2 SC 2.4.1 (Bypass Blocks). Every screen puts the header
		     controls and, on a tab destination, five tab buttons ahead of the
		     content, so a keyboard or switch user walked all of them on every
		     single navigation. The target already existed — #main-content has
		     been on the outlet all along — and only the way to reach it was
		     missing.

		     It is visible ONLY on focus, which is the standard treatment: the
		     first Tab press reveals it, everybody else never sees it. It must
		     not be `display: none` when unfocused, or it is not focusable at
		     all and the link does nothing. -->
		<a class="g-skip-link" href="#main-content">{{ __("Skip to main content") }}</a>
		<OfflineBanner />
		<ion-router-outlet id="main-content" />
		<Toasts />

		<UpdatePrompt />
		<InstallPrompt />
		<!-- Must-read notices open full screen on launch (alpha.7 §4.4). -->
		<MustReadNotice />
	</ion-app>
</template>

<script setup>
import { inject, onMounted } from "vue"
import { IonApp, IonRouterOutlet } from "@ionic/vue"

const __ = inject("$translate")

import { Toasts } from "frappe-ui"

import InstallPrompt from "@/components/InstallPrompt.vue"
import MustReadNotice from "@/components/MustReadNotice.vue"
import OfflineBanner from "@/components/OfflineBanner.vue"
import UpdatePrompt from "@/components/UpdatePrompt.vue"
import { showNotification } from "@/utils/pushNotifications"

onMounted(() => {
	window?.frappePushNotification?.onMessage((payload) => {
		showNotification(payload)
	})
})
</script>
