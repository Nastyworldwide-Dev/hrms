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
				<!-- The ticket exists but some files did not attach: keep the id, show
				     exactly which files failed, and let Submit become Retry — never a
				     second ticket for the same problem. -->
				<GBanner v-if="ticketName && failedFiles.length" variant="error">
					{{
						__("Ticket {0} is raised, but {1} file(s) did not upload:", [
							ticketName,
							failedFiles.length,
						])
					}}
					<ul class="mt-1 list-disc pl-5">
						<li v-for="f in failedFiles" :key="f.name">{{ f.name }} — {{ f.reason }}</li>
					</ul>
				</GBanner>

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
						:label="ticketName ? __('Retry uploads') : __('Submit ticket')"
						:pendingLabel="__('Submitting…')"
						:pending="newTicket.loading || uploading"
						:disabled="newTicket.loading || uploading"
					>
						<template #trailing>
							<FeatherIcon name="arrow-right" class="h-[17px] w-[17px]" aria-hidden="true" />
						</template>
					</GButton>
				</form>
			</div>
		</ion-content>
		<GConfirm
			:is-open="showDiscardDialog"
			:title="__('Discard this ticket?')"
			:confirm-label="__('Discard')"
			:cancel-label="__('Keep editing')"
			destructive
			@confirm="discardAndLeave"
			@cancel="showDiscardDialog = false"
		>
			{{ __("What you typed will be lost.") }}
		</GConfirm>
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
import GConfirm from "@/components/glass/GConfirm.vue"
import { IonContent } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"
import { computed, inject, reactive, ref } from "vue"
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
// Set once the ticket exists. From then on Submit only retries uploads.
const ticketName = ref(null)
const failedFiles = ref([])
const showDiscardDialog = ref(false)

ticketOptions.fetch()

const isDirty = computed(
	() =>
		Boolean(form.subject.trim() || form.description.trim() || files.value.length) &&
		!ticketName.value
)

function goBack() {
	if (isDirty.value) {
		showDiscardDialog.value = true
		return
	}
	// A raised ticket whose files failed is still a raised ticket: leaving
	// lands on it, not on Home, so the employee can attach from there later.
	if (ticketName.value) {
		router.replace({ name: "HelpdeskTicketDetail", params: { id: ticketName.value } })
		return
	}
	goBackOrHome(router)
}

function discardAndLeave() {
	showDiscardDialog.value = false
	goBackOrHome(router)
}

function validate() {
	errors.subject = form.subject.trim() ? "" : __("Give the ticket a subject.")
	errors.description = form.description.trim() ? "" : __("Tell us what is wrong.")
	return !errors.subject && !errors.description
}

async function uploadPending(name) {
	const pending = files.value.slice()
	if (!pending.length) return true
	uploading.value = true
	const results = await Promise.allSettled(
		pending.map((f) => new FileAttachment(f).upload("HD Ticket", name, ""))
	)
	uploading.value = false
	const failed = []
	results.forEach((result, index) => {
		if (result.status === "rejected") {
			const file = pending[index]
			failed.push({
				name: file.name,
				file,
				reason: result.reason?.messages?.[0] || result.reason?.message || __("upload failed"),
			})
		}
	})
	// Only the failures stay selectable, so a retry re-sends exactly those.
	files.value = failed.map((f) => f.file)
	failedFiles.value = failed
	console.info("[TicketNew] uploads for", name, "failed:", failed.length, "of", pending.length)
	return failed.length === 0
}

async function submit() {
	errorMessage.value = ""
	try {
		if (!ticketName.value) {
			if (!validate()) return
			const { name } = await newTicket.submit({
				subject: form.subject.trim(),
				description: form.description.trim(),
				ticket_type: form.ticket_type || undefined,
				priority: form.priority || undefined,
			})
			ticketName.value = name
			console.info("[TicketNew] raised", name, "with", files.value.length, "file(s)")
		}
		if (!(await uploadPending(ticketName.value))) return
		myTickets.reload?.()
		router.replace({ name: "HelpdeskTicketDetail", params: { id: ticketName.value } })
	} catch (error) {
		uploading.value = false
		errorMessage.value = error?.messages?.[0] || __("Could not raise the ticket. Try again.")
		console.warn("[TicketNew] submit failed:", errorMessage.value)
	}
}
</script>
