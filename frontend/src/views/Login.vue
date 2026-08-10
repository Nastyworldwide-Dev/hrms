<template>
	<ion-page>
		<ion-content class="ion-no-padding">
			<div class="flex h-screen w-screen bg-ground">
				<!-- Accent side panel (tablet / desktop only) -->
				<div
					class="hidden lg:flex lg:w-[44%] bg-accent text-ground flex-col justify-between p-10"
				>
					<FrappeHRLogo class="h-12 w-12" />
					<div>
						<div
							class="font-sans font-extrabold text-5xl leading-[1.05] tracking-tight"
						>
							{{ __("Employee") }}<br />{{ __("self-service.") }}
						</div>
						<div class="text-[13px] mt-3.5 opacity-85">
							{{ __("Attendance · Leaves · Expenses · Payroll") }}
						</div>
					</div>
					<div class="text-[10px] uppercase tracking-[0.1em] font-extrabold opacity-70">
						{{ __("Frappe HR · Mobile & Tablet") }}
					</div>
				</div>

				<!-- Login form -->
				<div
					class="flex-1 flex flex-col justify-center px-7 lg:px-[72px]"
				>
					<div class="mx-auto w-full max-w-[360px]">
						<FrappeHRLogo class="h-11 w-11 lg:hidden" />
						<h1
							class="font-sans font-extrabold text-[30px] leading-[1.08] tracking-tight mt-5 lg:mt-0 mb-1.5"
						>
							{{ __("Login to Frappe HR") }}<span class="text-accent">.</span>
						</h1>
						<p class="text-[13px] text-ink-600 mb-7">
							{{ __("Employee self-service portal") }}
						</p>

						<form
							v-if="!user_pass_login_disabled.data"
							class="flex flex-col gap-4"
							@submit.prevent="submit"
						>
							<div>
								<label class="block text-xs mb-1.5 text-ink-700">{{ __("Email") }}</label>
								<input
									v-model="email"
									type="text"
									autocomplete="username"
									:placeholder="__('johndoe@mail.com')"
									class="w-full min-h-[38px] px-2.5 py-1.5 text-sm bg-surface border border-divider text-inkbase caret-accent outline-none focus:border-accent"
								/>
							</div>
							<div>
								<label class="block text-xs mb-1.5 text-ink-700">{{ __("Password") }}</label>
								<input
									v-model="password"
									type="password"
									autocomplete="current-password"
									placeholder="••••••"
									class="w-full min-h-[38px] px-2.5 py-1.5 text-sm bg-surface border border-divider text-inkbase caret-accent outline-none focus:border-accent"
								/>
								<div class="flex justify-end mt-1.5">
									<button
										type="button"
										class="text-xs text-ink-700 underline underline-offset-[3px] py-2.5 -my-1.5 px-1 -mx-1"
										@click="openForgotDialog"
									>
										{{ __("Forgot Password?") }}
									</button>
								</div>
							</div>
							<ErrorMessage :message="errorMessage" />
							<button
								type="submit"
								class="m-btn-primary !mt-2 disabled:opacity-60"
								:disabled="session.login.loading"
							>
								<span>{{ __("Login") }}</span>
								<LoadingIndicator v-if="session.login.loading" class="w-4 h-4 ml-auto" />
								<svg
									v-else
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									class="ml-auto"
								>
									<line x1="5" y1="12" x2="19" y2="12"></line>
									<polyline points="12 5 19 12 12 19"></polyline>
								</svg>
							</button>
						</form>

						<template v-if="authProviders.data?.length">
							<div v-if="!user_pass_login_disabled.data" class="text-center text-sm text-ink-600 my-4">or</div>
							<div class="flex flex-col gap-3">
								<a
									v-for="provider in authProviders.data"
									:key="provider.name"
									class="flex items-center justify-center gap-2 transition-colors focus:outline-none text-inkbase bg-surface border border-divider hover:bg-ink-200 h-9 text-sm px-2"
									:href="provider.auth_url"
								>
									<img class="h-4 w-4" :src="provider.icon" :alt="provider.provider_name" />
									<span>Login with {{ provider.provider_name }}</span>
								</a>
							</div>
						</template>

						<div v-else-if="user_pass_login_disabled.data" class="text-center text-ink-600 py-8">{{ __("No login methods are available. Please contact your administrator.") }}</div>
					</div>
				</div>
			</div>

			<Dialog v-model="resetPassword.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("Reset Password") }} </h2>
				</template>
				<template #body-content>
					<p>
						{{ __("Your password has expired. Please reset your password to continue") }}
					</p>
				</template>
				<template #actions>
					<a
						class="inline-flex items-center justify-center gap-2 transition-colors focus:outline-none text-ground bg-accent hover:bg-accent-600 active:bg-accent-800 focus-visible:ring focus-visible:ring-accent-300 h-8 text-sm font-bold px-3"
						:href="resetPassword.link"
						target="_blank"
					>
						{{ __("Go to Reset Password page") }}
					</a>
				</template>
			</Dialog>

			<Dialog v-model="forgot.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("Forgot Password") }}</h2>
				</template>
				<template #body-content>
					<form class="flex flex-col space-y-4" @submit.prevent="sendResetLink">
						<Input
							:label="__('Email')"
							type="text"
							:placeholder="__('johndoe@mail.com')"
							v-model="forgot.email"
							autocomplete="username"
						/>
						<ErrorMessage :message="forgot.error" />
						<p v-if="forgot.sent" class="text-sm text-accent-700">
							{{ __("If this email is registered, password reset instructions have been sent to it.") }}
						</p>
						<Button
							v-else
							:loading="forgot.loading"
							variant="solid"
							class="!bg-accent hover:!bg-accent-600 !text-ground disabled:opacity-60 !mt-2"
						>
							{{ __("Send Reset Link") }}
						</Button>
					</form>
				</template>
			</Dialog>

			<Dialog v-model="otp.showDialog">
				<template #body-title>
					<h2 class="text-lg font-bold">{{ __("OTP Verification") }}</h2>
				</template>
				<template #body-content>
					<p class="mb-4" v-if="otp.verification.prompt">
						{{ otp.verification.prompt }}
					</p>

					<form class="flex flex-col space-y-4" @submit.prevent="submit">
						<Input
							:label="__('OTP Code')"
							type="text"
							placeholder="000000"
							v-model="otp.code"
							autocomplete="one-time-code"
						/>
						<ErrorMessage :message="errorMessage" />
						<Button
							:loading="session.otp.loading"
							variant="solid"
							class="!bg-accent hover:!bg-accent-600 !text-ground disabled:opacity-60 !mt-6"
						>
							{{ __("Verify") }}
						</Button>
					</form>
				</template>
			</Dialog>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { IonPage, IonContent } from "@ionic/vue"
import { inject, reactive, ref } from "vue"
import { Input, Button, ErrorMessage, Dialog, LoadingIndicator, createResource } from "frappe-ui"

import FrappeHRLogo from "@/components/icons/FrappeHRLogo.vue"
import { sendPasswordResetLink } from "@/utils/resetPassword"

const email = ref(null)
const password = ref(null)
const errorMessage = ref("")

const forgot = reactive({
	showDialog: false,
	email: "",
	error: "",
	sent: false,
	loading: false,
})

function openForgotDialog() {
	forgot.email = email.value || ""
	forgot.error = ""
	forgot.sent = false
	forgot.showDialog = true
}

async function sendResetLink() {
	if (!forgot.email) {
		forgot.error = __("Please enter your email")
		return
	}
	forgot.error = ""
	forgot.loading = true
	try {
		await sendPasswordResetLink(forgot.email.trim())
		forgot.sent = true
		console.info("[Login] Password reset link requested")
	} catch (err) {
		forgot.error = __(err.message)
	} finally {
		forgot.loading = false
	}
}

const resetPassword = reactive({
	showDialog: false,
	link: "",
})
const otp = reactive({
	showDialog: false,
	tmp_id: "",
	code: "",
	verification: {},
})

const session = inject("$session")
const __ = inject("$translate")

async function submit(e) {
	try {
		let response
		if (otp.showDialog) {
			response = await session.otp(otp.tmp_id, otp.code)
		} else {
			response = await session.login(email.value, password.value)
		}

		if (response.message === "Password Reset") {
			resetPassword.showDialog = true
			resetPassword.link = response.redirect_to
		} else {
			resetPassword.showDialog = false
			resetPassword.link = ""
		}

		// OTP verification
		if (response.verification) {
			if (response.verification.setup) {
				otp.showDialog = true
				otp.tmp_id = response.tmp_id
				otp.verification = response.verification
			} else {
				// Don't bother handling impossible OTP setup (e.g. no phone number).
				window.open("/login?redirect-to=" + encodeURIComponent(window.location.pathname), "_blank")
			}
		}
	} catch (error) {
		errorMessage.value = error.messages.join("\n")
	}
}

const user_pass_login_disabled = createResource({
	url: "hrms.api.system_settings.get_user_pass_login_disabled",
	method: 'GET',
	initialData: 1,
	auto: true,
})

const authProviders = createResource({
	url: "hrms.api.oauth.oauth_providers",
	auto: true,
})
</script>
