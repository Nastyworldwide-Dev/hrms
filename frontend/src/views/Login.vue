<template>
	<GPage :field="false">
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
						<div class="text-card-title mt-3.5 opacity-85">
							{{ __("Attendance · Leaves · Expenses · Payroll") }}
						</div>
					</div>
					<div class="text-micro-label uppercase font-extrabold opacity-70">
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
							class="font-sans font-extrabold text-display-number tracking-tight mt-5 lg:mt-0 mb-1.5"
						>
							{{ __("Login to Frappe HR") }}<span class="text-accent">.</span>
						</h1>
						<p class="text-card-title text-ink-600 mb-7">
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
										class="text-xs text-ink-700 underline underline-offset-link py-2.5 -my-1.5 px-1 -mx-1"
										@click="openForgotDialog"
									>
										{{ __("Forgot Password?") }}
									</button>
								</div>
							</div>
							<ErrorMessage :message="errorMessage" />
							<GButton
								type="submit"
								class="!mt-2"
								:label="__('Login')"
								:pending-label="__('Signing in…')"
								:pending="session.login.loading"
							>
								<template #trailing>
									<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
										<line x1="5" y1="12" x2="19" y2="12"></line>
										<polyline points="12 5 19 12 12 19"></polyline>
									</svg>
								</template>
							</GButton>
						</form>

						<template v-if="authProviders.data?.length">
							<div v-if="!user_pass_login_disabled.data" class="text-center text-sm text-ink-600 my-4">or</div>
							<div class="flex flex-col gap-3">
								<GProviderButton
									v-for="provider in authProviders.data"
									:key="provider.name"
									:name="provider.provider_name"
									:icon="provider.icon"
									:href="provider.auth_url"
								/>
							</div>
						</template>

						<div v-else-if="user_pass_login_disabled.data" class="text-center text-ink-600 py-8">{{ __("No login methods are available. Please contact your administrator.") }}</div>
					</div>
				</div>
			</div>

			<!-- Deferred from 5.1: these three hold forms with their own
			     validation, not confirmations, so they needed the batch that owns
			     Login. GModal carries the focus-trap workaround (§16.3), which
			     matters most here — an OTP field inside a trapped ion-modal is
			     exactly the bug that workaround exists for. -->
			<GModal
				:is-open="resetPassword.showDialog"
				:title="__('Reset password')"
				@did-dismiss="resetPassword.showDialog = false"
			>
				<p class="g-confirm__body">
					{{ __("Your password has expired. Please reset your password to continue") }}
				</p>
				<a class="g-provider" :href="resetPassword.link" target="_blank">
					{{ __("Go to Reset Password page") }}
				</a>
			</GModal>

			<GModal
				:is-open="forgot.showDialog"
				:title="__('Forgot password')"
				@did-dismiss="forgot.showDialog = false"
			>
				<form class="flex flex-col gap-stack-md" @submit.prevent="sendResetLink">
					<GInput
						v-model="forgot.email"
						:label="__('Email')"
						:placeholder="__('johndoe@mail.com')"
						:error="forgot.error"
						autocomplete="username"
					/>
					<p v-if="forgot.sent" class="g-confirm__body">
						{{ __("If this email is registered, password reset instructions have been sent to it.") }}
					</p>
					<GButton
						v-else
						type="submit"
						:label="__('Send Reset Link')"
						:pending-label="__('Sending…')"
						:pending="forgot.loading"
					/>
				</form>
			</GModal>

			<GModal
				:is-open="otp.showDialog"
				:title="__('OTP verification')"
				@did-dismiss="otp.showDialog = false"
			>
				<p v-if="otp.verification.prompt" class="g-confirm__body">
					{{ otp.verification.prompt }}
				</p>
				<form class="flex flex-col gap-stack-md" @submit.prevent="submit">
					<GInput
						v-model="otp.code"
						:label="__('OTP Code')"
						placeholder="000000"
						:error="errorMessage"
						autocomplete="one-time-code"
					/>
					<GButton
						type="submit"
						:label="__('Verify')"
						:pending-label="__('Verifying…')"
						:pending="session.otp.loading"
					/>
				</form>
			</GModal>
		</ion-content>
	</GPage>
</template>

<script setup>
import GInput from "@/components/glass/GInput.vue"
import GModal from "@/components/glass/GModal.vue"
import GProviderButton from "@/components/glass/GProviderButton.vue"
import GPage from "@/components/glass/GPage.vue"
import GButton from "@/components/glass/GButton.vue"
import { IonContent } from "@ionic/vue"
import { inject, reactive, ref } from "vue"
import { Input, Button, ErrorMessage, createResource } from "frappe-ui"

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
