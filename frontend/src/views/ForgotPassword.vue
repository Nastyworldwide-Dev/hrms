<template>
	<GPage>
		<ion-content :fullscreen="true">
			<!-- 8.5 — this screen was never migrated. It imported GPage, GInput and
			     GButton but used only GPage, and a hardcoded `bg-white` on the
			     container painted over the theme: the dark capture rendered a
			     white page with a near-white primary on it. No bg-* here now, so
			     the page background and the light field show through. -->
			<div class="flex flex-col h-full w-full">
				<div class="w-full h-full sm:w-96 flex flex-col">
					<header
						class="flex flex-row bg-ground py-4 px-3 items-center sticky top-0 z-sticky border-b border-divider"
					>
						<GIconButton :label="__('Back')" flush class="mr-1" @click="goBack">
							<FeatherIcon name="chevron-left" class="h-5 w-5 text-inkbase" />
						</GIconButton>
						<h2 class="text-xl font-extrabold text-inkbase tracking-tight">
							{{ __("Reset Password") }}
						</h2>
					</header>

					<div class="grow overflow-y-auto">
						<form class="flex flex-col space-y-4 p-4" @submit.prevent="sendPasswordReset">
							<p class="text-card-title text-ink-600">
								{{
									__("Enter your email address and we'll send you a link to reset your password.")
								}}
							</p>
							<GInput
								:label="__('Email') + ' *'"
								type="email"
								placeholder="johndoe@mail.com"
								v-model="email"
								autocomplete="username"
								:error="errorMessage"
							/>
						</form>
					</div>

					<div
						class="px-4 pt-4 pb-4 standalone:pb-safe-bottom sm:w-96 bg-ground sticky bottom-0 w-full z-40 border-t border-divider"
					>
						<GButton
							:label="__('Send Reset Link')"
							:pending-label="__('Sending…')"
							:pending="forgotPasswordResource.loading"
							@click="sendPasswordReset"
						/>
					</div>
				</div>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GIconButton from "@/components/glass/GIconButton.vue"
import GButton from "@/components/glass/GButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GPage from "@/components/glass/GPage.vue"
import { IonContent } from "@ionic/vue"
import { useRoute, useRouter } from "vue-router"
import { FeatherIcon, toast, createResource } from "frappe-ui"

import { inject, ref } from "vue"

const __ = inject("$translate")
const route = useRoute()
const router = useRouter()

const email = ref(
	Array.isArray(route.query.email) ? route.query.email[0] : route.query.email || ""
)
const errorMessage = ref("")

const forgotPasswordResource = createResource({
	url: "frappe.core.doctype.user.user.reset_password",
	method: "POST",
	onSuccess() {
		toast({
			title: __("Success"),
			text: __("Password reset link has been sent to your email."),
			icon: "check-circle",
			position: "bottom-center",
			iconClasses: "text-green-500",
		})
		errorMessage.value = ""
		router.replace({ name: "Login" })
	},
	onError(error) {
		errorMessage.value = error.messages?.[0] || __("Failed to send reset link")
	},
})

function isValidEmail(value) {
	return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

function goBack() {
	if (window.history.state?.back) {
		router.back()
		return
	}

	router.replace({ name: "Login" })
}

function sendPasswordReset() {
	const emailValue = (email.value || "").trim()

	if (!emailValue) {
		errorMessage.value = __("Please enter your email address")
		return
	}

	if (!isValidEmail(emailValue)) {
		errorMessage.value = __("Please enter a valid email address")
		return
	}

	errorMessage.value = ""
	forgotPasswordResource.submit({ user: emailValue })
}
</script>
