<template>
	<ion-page>
		<ion-header class="ion-no-border">
			<div class="w-full max-w-md mx-auto lg:max-w-none lg:mx-0">
				<div
					class="flex flex-row justify-between items-center bg-ground border-b-2 border-divider px-4 py-3.5 lg:h-16 lg:px-7 lg:py-0"
				>
					<h2
						class="font-extrabold tracking-tight text-lg lg:text-[19px] text-inkbase"
					>
						{{ props.pageTitle || __("Frappe HR") }}
					</h2>
					<div class="flex flex-row items-center gap-3.5 lg:gap-4 ml-auto">
						<span
							class="hidden lg:inline text-[10px] uppercase tracking-[0.1em] text-ink-600"
						>
							{{ dateKicker }}
						</span>
						<router-link
							:to="{ name: 'Notifications' }"
							v-slot="{ navigate }"
							class="flex flex-col items-center"
							:aria-label="__('Notifications')"
						>
							<span class="relative inline-block" @click="navigate">
								<FeatherIcon name="bell" class="h-5 w-5" />
								<span
									v-if="unreadNotificationsCount.data"
									class="absolute top-0 right-0.5 inline-block w-2 h-2 bg-accent"
								>
								</span>
							</span>
						</router-link>
						<router-link
							:to="{ name: 'Profile' }"
							class="flex flex-col items-center lg:hidden m-avatar-sq"
						>
							<Avatar
								:image="user.data.user_image"
								:label="user.data.first_name"
								size="xl"
							/>
						</router-link>
					</div>
				</div>
			</div>
		</ion-header>

		<ion-content class="ion-no-padding">
			<div
				class="flex flex-col h-screen w-full max-w-md mx-auto lg:max-w-none lg:mx-0"
			>
				<slot name="body"></slot>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonHeader, IonContent, IonPage } from "@ionic/vue"
import { FeatherIcon, Avatar } from "frappe-ui"

import { unreadNotificationsCount } from "@/data/notifications"

import { inject, computed } from "vue"

const user = inject("$user")
const $dayjs = inject("$dayjs")
const __ = inject("$translate")

// Uppercase long date shown on the lg+ header (e.g. "THURSDAY, 23 JULY 2026").
const dateKicker = computed(() =>
	$dayjs().format("dddd, D MMMM YYYY").toUpperCase()
)

const props = defineProps({
	pageTitle: {
		type: String,
		required: false,
		default: "",
	},
})
</script>
