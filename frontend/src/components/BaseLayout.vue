<template>
	<GPage>
		<ion-header class="ion-no-border g-page__content">
			<div class="w-full max-w-md mx-auto lg:max-w-none lg:mx-0">
				<GAppHeader
					:title="props.pageTitle"
					:unread="unreadNotificationsCount.data || 0"
					:avatar-url="user.data?.user_image"
					:avatar-label="user.data?.first_name"
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
import { inject } from "vue"

const router = useRouter()
const user = inject("$user")
const __ = inject("$translate")

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})
</script>
