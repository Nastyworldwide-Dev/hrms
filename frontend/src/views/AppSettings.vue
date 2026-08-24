<template>
	<GPage>
		<ion-content class="ion-padding">
			<div class="flex flex-col min-h-full w-full">
				<div class="w-full max-w-[620px] mx-auto">
					<header
						class="flex flex-row py-3.5 px-4 items-center justify-between border-b-2 border-divider sticky top-0 z-sticky bg-ground"
					>
						<div class="flex flex-row items-center gap-2.5">
							<GIconButton :label="__('Back')" flush @click="router.back()">
								<FeatherIcon name="chevron-left" class="h-5 w-5" />
							</GIconButton>
							<h2 class="font-sans font-extrabold text-lg tracking-tight text-inkbase">{{ __("Settings") }}</h2>
						</div>
					</header>

					<div class="flex flex-col gap-4 w-full p-4">
						<span class="g-eyebrow">{{ __("Appearance") }}</span>
						<div class="flex flex-col gap-3.5 border-t-2 border-divider pt-4 mb-2">
							<div class="flex items-center gap-3">
								<FeatherIcon name="moon" class="h-[18px] w-[18px] text-accent-ink" />
								<div class="flex flex-col">
									<span class="text-sm font-semibold text-inkbase">
										{{ __("Theme") }}
									</span>
									<span class="text-xs text-ink-600">{{ currentThemeLabel }}</span>
								</div>
							</div>
							<div class="flex w-full border border-divider rounded-input overflow-hidden">
								<button
									v-for="mode in THEME_MODES"
									:key="mode"
									type="button"
									class="g-eyebrow-type g-touch flex-1 py-2 border-r border-divider last:border-r-0"
									:class="
										theme.mode === mode
											? 'bg-inkbase text-ground'
											: 'bg-transparent text-ink-700 hover:bg-inkbase/[0.04]'
									"
									@click="setTheme(mode, $event)"
								>
									{{ __(themeLabels[mode]) }}
								</button>
							</div>
						</div>
						<span class="g-eyebrow">{{ __("Notifications") }}</span>
						<!-- frappe-ui's Switch renders a 32×20 button and does not forward
						     a class to it, and its row is not clickable — so that button was
						     the whole target. The wrapper lets the theme expand its hit area
						     to §14.1 without changing the toggle's visual. -->
						<div class="flex flex-col border-t-2 border-divider pt-4 g-switch-row">
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
							<GSkeleton height="14px" width="42%" />
							<span class="text-inkbase text-sm">
								{{ pushNotificationState ? __("Disabling Push Notifications...") : __("Enabling Push Notifications...") }}
							</span>
						</div>

						<span class="g-eyebrow">{{ __("Account") }}</span>
						<div class="flex flex-col border-t-2 border-divider pt-1">
							<router-link
								:to="{ name: 'ChangePassword' }"
								class="flex flex-row cursor-pointer p-4 pl-0.5 items-center justify-between border-b border-divider hover:bg-inkbase/[0.04]"
							>
								<div class="flex flex-row items-center gap-3 grow">
									<FeatherIcon name="lock" class="h-[18px] w-[18px] text-inkbase" />
									<div class="text-button-label text-inkbase">
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
	</GPage>
</template>

<script setup>
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { useRouter } from "vue-router"
import { FeatherIcon, Switch, toast } from "frappe-ui"
import GIconButton from "@/components/glass/GIconButton.vue"

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