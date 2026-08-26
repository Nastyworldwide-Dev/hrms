<template>
	<GPage>
		<ion-header class="ion-no-border g-page__content">
			<div class="w-full max-w-md mx-auto lg:max-w-none lg:mx-0">
				<GAppHeader
					:title="props.pageTitle || __('Nadi')"
					:unread="unreadNotificationsCount.data || 0"
					:kicker="dateKicker"
					:avatar-url="user.data.user_image"
					:avatar-label="user.data.first_name"
					@notifications="router.push({ name: 'Notifications' })"
					@profile="router.push({ name: 'Profile' })"
					@back="router.back()"
				/>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding g-page__content">
			<div class="flex flex-col min-h-full w-full max-w-md mx-auto lg:max-w-none lg:mx-0">
				<slot name="body"></slot>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import GAppHeader from "@/components/glass/GAppHeader.vue"
import { IonHeader, IonContent } from "@ionic/vue"

import { unreadNotificationsCount } from "@/data/notifications"

import { useRouter } from "vue-router"
import { inject, computed } from "vue"

const router = useRouter()
const user = inject("$user")
const $dayjs = inject("$dayjs")
const __ = inject("$translate")

// Uppercase long date shown on the lg+ header (e.g. "THURSDAY, 23 JULY 2026").
const dateKicker = computed(() => $dayjs().format("dddd, D MMMM YYYY").toUpperCase())

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})
</script>
