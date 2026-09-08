<template>
	<GPage>
		<ion-content :fullscreen="true">
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full lg:p-7 max-w-content-column-lg mx-auto"
			>
				<div class="flex flex-row items-center gap-2.5">
					<GIconButton :label="__('Back')" @click="goBack">
						<FeatherIcon name="chevron-left" class="h-4 w-4" />
					</GIconButton>
					<span class="text-xl font-extrabold text-inkbase">{{ __("New ticket") }}</span>
				</div>

				<GBanner v-if="errorMessage" variant="error">{{ errorMessage }}</GBanner>

				<form class="flex flex-col gap-4" novalidate @submit.prevent="submit">
					<GInput
						v-model="form.subject"
						:label="__('Subject')"
						:placeholder="__('e.g. Cannot sign in to email')"
						:error="errors.subject"
					/>

					<div class="grid grid-cols-2 gap-3">
						<label class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Type") }}</span>
							<select v-model="form.ticket_type" class="g-input">
								<option value="">{{ __("Select") }}</option>
								<option v-for="t in ticketOptions.data?.types || []" :key="t" :value="t">
									{{ t }}
								</option>
							</select>
						</label>
						<label class="flex flex-col gap-1.5">
							<span class="g-eyebrow">{{ __("Priority") }}</span>
							<select v-model="form.priority" class="g-input">
								<option value="">{{ __("Default") }}</option>
								<option v-for="p in ticketOptions.data?.priorities || []" :key="p" :value="p">
									{{ p }}
								</option>
							</select>
						</label>
					</div>

					<GTextarea
						v-model="form.description"
						:label="__('Describe the problem')"
						:placeholder="__('What happened, when it started, and what you already tried')"
						:error="errors.description"
					/>

					<GFileUpload v-model="files" :label="__('Screenshot or file')" :uploading="uploading" />

					<GButton
						type="submit"
						:label="__('Submit ticket')"
						:pendingLabel="__('Submitting…')"
						:pending="newTicket.loading || uploading"
						:disabled="newTicket.loading || uploading"
					>
						<template #trailing>
							<svg
								width="17"
								height="17"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
							>
								<line x1="5" y1="12" x2="19" y2="12"></line>
								<polyline points="12 5 19 12 12 19"></polyline>
							</svg>
						</template>
					</GButton>
				</form>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import GBanner from "@/components/glass/GBanner.vue"
import GButton from "@/components/glass/GButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GInput from "@/components/glass/GInput.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import GFileUpload from "@/components/glass/GFileUpload.vue"
import { IonContent } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"
import { inject, reactive, ref } from "vue"
import { useRouter } from "vue-router"

import { FileAttachment } from "@/composables"
import { myTickets, newTicket, ticketOptions } from "@/data/helpdesk"
import { goBackOrHome } from "@/utils/navigation"

const router = useRouter()
const __ = inject("$translate")

const form = reactive({ subject: "", description: "", ticket_type: "", priority: "" })
const errors = reactive({ subject: "", description: "" })
const files = ref([])
const uploading = ref(false)
const errorMessage = ref("")

ticketOptions.fetch()

function goBack() {
	goBackOrHome(router)
}

function validate() {
	errors.subject = form.subject.trim() ? "" : __("Give the ticket a subject.")
	errors.description = form.description.trim() ? "" : __("Tell us what is wrong.")
	return !errors.subject && !errors.description
}

async function submit() {
	errorMessage.value = ""
	if (!validate()) return
	try {
		const { name } = await newTicket.submit({
			subject: form.subject.trim(),
			description: form.description.trim(),
			ticket_type: form.ticket_type || undefined,
			priority: form.priority || undefined,
		})
		console.info("[TicketNew] raised", name, "with", files.value.length, "file(s)")
		if (files.value.length) {
			uploading.value = true
			await Promise.allSettled(
				files.value.map((f) => new FileAttachment(f).upload("HD Ticket", name, ""))
			)
			uploading.value = false
		}
		myTickets.reload?.()
		router.replace({ name: "HelpdeskTicketDetail", params: { id: name } })
	} catch (error) {
		uploading.value = false
		errorMessage.value = error?.messages?.[0] || __("Could not raise the ticket. Try again.")
		console.warn("[TicketNew] submit failed:", errorMessage.value)
	}
}
</script>
