<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen bg-ground">
				<div class="w-full max-w-[620px] mx-auto">
					<header
						class="flex flex-row bg-ground py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-10"
					>
						<div class="flex flex-row items-center gap-2.5">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-transparent"
								@click="router.back()"
							>
								<FeatherIcon name="arrow-left" class="h-5 w-5" />
							</Button>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">{{ __("Settings") }}</h2>
						</div>
					</header>

					<div class="flex flex-col gap-4 w-full p-4">
						<span class="m-kicker">{{ __("Appearance") }}</span>
						<div class="flex flex-col gap-3.5 border-t-2 border-divider pt-4 mb-2">
							<div class="flex items-center gap-3">
								<FeatherIcon name="moon" class="h-[18px] w-[18px] text-accent" />
								<div class="flex flex-col">
									<span class="text-sm font-semibold text-inkbase">
										{{ __("Theme") }}
									</span>
									<span class="text-xs text-ink-600">{{ currentThemeLabel }}</span>
								</div>
							</div>
							<div class="flex w-full border border-divider">
								<button
									v-for="mode in THEME_MODES"
									:key="mode"
									type="button"
									class="flex-1 py-2 text-[11px] uppercase tracking-[0.08em] font-sans font-extrabold border-r border-divider last:border-r-0"
									:class="
										theme.mode === mode
											? 'bg-accent text-ground'
											: 'bg-transparent text-ink-700 hover:bg-inkbase/[0.04]'
									"
									@click="setTheme(mode, $event)"
								>
									{{ __(themeLabels[mode]) }}
								</button>
							</div>
						</div>
						<span class="m-kicker">{{ __("Notifications") }}</span>
						<div class="flex flex-col border-t-2 border-divider pt-4">
							<Switch
								size="md"
								:label="__('Enable Push Notifications')"
								:class="description ? 'p-2' : ''"
								:model-value="pushNotificationState"
								:disabled="disablePushSetting"
								:description="description"
								@update:model-value="togglePushNotifications"
							/>
						</div>

						<div
							v-if="isLoading"
							class="flex -mt-1 items-center gap-2"
						>
							<LoadingIndicator class="w-3 h-3 text-inkbase" />
							<span class="text-inkbase text-sm">
								{{ pushNotificationState ? __("Disabling Push Notifications...") : __("Enabling Push Notifications...") }}
							</span>
						</div>

						<span class="m-kicker">{{ __("Account") }}</span>
						<div class="flex flex-col border-t-2 border-divider pt-1">
							<router-link
								:to="{ name: 'ChangePassword' }"
								class="flex flex-row cursor-pointer p-4 pl-0.5 items-center justify-between border-b border-divider hover:bg-inkbase/[0.04]"
							>
								<div class="flex flex-row items-center gap-3 grow">
									<FeatherIcon name="lock" class="h-[18px] w-[18px] text-inkbase" />
									<div class="text-[15px] text-inkbase">
										{{ __("Change Password") }}
									</div>
								</div>
								<FeatherIcon name="chevron-right" class="h-[18px] w-[18px] text-ink-600" />
							</router-link>
						</div>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import { FeatherIcon, Switch, toast, LoadingIndicator, Button } from "frappe-ui"

import { computed, inject, ref } from "vue"

import {
	arePushNotificationsEnabled,
	enablePushNotifications as requestPushEnable,
} from "@/data/notifications"
import { theme, setTheme, THEME_MODES } from "@/data/theme"

const __ = inject("$translate")
const router = useRouter()

// __("Light"), __("Dark"), __("System"), __("System default")
const themeLabels = { light: "Light", dark: "Dark", system: "System" }
const currentThemeLabel = computed(() =>
	theme.mode === "system" ? __("System default") : __(themeLabels[theme.mode])
)
const pushNotificationState = ref(
	window.frappePushNotification?.isNotificationEnabled()
)
const isLoading = ref(false)

const disablePushSetting = computed(() => {
	return (
		!(
			window.frappe?.boot.push_relay_server_url &&
			arePushNotificationsEnabled.data
		) || isLoading.value
	)
})

const description = computed(() => {
	return !(
		window.frappe?.boot.push_relay_server_url &&
		arePushNotificationsEnabled.data
	)
		? __("Push notifications have been disabled on your site")
		: ""
})

const togglePushNotifications = (newValue) => {
	if (newValue) {
		enablePushNotifications()
	} else {
		isLoading.value = true
		window.frappePushNotification
			.disableNotification()
			.then(() => {
				pushNotificationState.value = false
				toast({
					title: __("Success"),
					text: __("Push notifications disabled"),
					icon: "check-circle",
					position: "bottom-center",
					iconClasses: "text-green-500",
				})
			})
			.catch((error) => {
				toast({
					title: __("Error"),
					text: __(error.message),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			})
			.finally(() => {
				isLoading.value = false
			})
	}
}
const enablePushNotifications = () => {
	isLoading.value = true

	requestPushEnable()
		.then((data) => {
			if (data.permission_granted) {
				pushNotificationState.value = true
			} else {
				toast({
					title: __("Error"),
					text: __("Push Notification permission denied"),
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
				pushNotificationState.value = false
			}
		})
		.catch((error) => {
			toast({
				title: __("Error"),
				text: __(error.message),
				icon: "alert-circle",
				position: "bottom-center",
				iconClasses: "text-red-500",
			})
			pushNotificationState.value = false
		})
		.finally(() => {
			isLoading.value = false
		})
}

</script>