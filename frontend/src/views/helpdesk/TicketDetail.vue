<template>
	<GPage>
		<ion-content :fullscreen="true">
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full lg:p-7 max-w-content-column-lg mx-auto"
			>
				<div class="flex flex-row items-center gap-2.5 min-w-0">
					<GIconButton :label="__('Back')" @click="goBack">
						<FeatherIcon name="chevron-left" class="h-4 w-4" />
					</GIconButton>
					<span class="text-lg font-extrabold text-inkbase truncate flex-1 min-w-0">
						{{ ticket?.subject || props.id }}
					</span>
					<GStatusChip
						v-if="ticket?.status"
						class="flex-none"
						:status="ticket.status"
						:label="__(statusLabel(ticket.status))"
					/>
				</div>

				<ResourceError :resource="ticketDetail" back what="this ticket" />
				<GSkeleton v-if="ticketDetail.loading && !ticket" height="220px" />

				<template v-if="ticket">
					<!-- meta grid: ONE glass surface with hair dividers (§15.2). The
					     first cell is WHO raised it — the HRM's own addition. -->
					<div class="g-glass grid grid-cols-2 rounded-panel overflow-hidden">
						<div
							v-for="(cell, i) in metaCells"
							:key="cell.k"
							class="flex flex-col gap-0.5 px-3.5 py-3 border-divider"
							:class="[i % 2 === 0 ? 'border-r' : '', i < 2 ? 'border-b' : '']"
						>
							<span class="g-eyebrow">{{ cell.k }}</span>
							<span class="font-semibold text-inkbase truncate">{{ cell.v }}</span>
						</div>
					</div>

					<span class="g-eyebrow mt-1">{{ __("Conversation") }}</span>
					<div class="flex flex-col gap-2.5">
						<div
							v-for="m in thread"
							:key="m.id"
							class="max-w-[86%] px-3.5 py-3 rounded-2xl text-sm leading-relaxed"
							:class="
								m.kind === 'me'
									? 'self-end bg-accent-ink/10 border border-accent-ink/40 rounded-br-md'
									: 'self-start g-glass rounded-bl-md'
							"
						>
							<div class="text-caption font-bold text-ink-600 mb-1">
								{{ m.who }} · {{ formatWhen(m.when) }}
							</div>
							<!-- Helpdesk stores rich text; sanitised server-side by frappe -->
							<div class="prose-sm break-words" v-html="m.html" />
						</div>
						<GEmptyState
							v-if="!thread.length"
							:title="__('No messages yet')"
							:body="__('The Helpdesk team will reply here.')"
						/>
					</div>

					<span v-if="isResolved" class="text-caption text-ink-600 text-center">
						{{ __("This ticket is resolved. Replying will reopen it.") }}
					</span>

					<form class="flex flex-row items-end gap-2 sticky bottom-0 pt-2" @submit.prevent="send">
						<GTextarea
							v-model="reply"
							class="flex-1"
							:label="__('Reply')"
							:placeholder="__('Write a reply…')"
						/>
						<GButton
							type="submit"
							class="flex-none !w-auto"
							:label="__('Send')"
							:pendingLabel="__('Sending…')"
							:pending="replyToTicket.loading"
							:disabled="replyToTicket.loading || !reply.trim()"
						/>
					</form>
				</template>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import GPage from "@/components/glass/GPage.vue"
import GButton from "@/components/glass/GButton.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import { IonContent } from "@ionic/vue"
import { FeatherIcon } from "frappe-ui"
import { computed, inject, ref, watch } from "vue"
import { useRouter } from "vue-router"

import ResourceError from "@/components/ResourceError.vue"
import { myTickets, replyToTicket, ticketDetail } from "@/data/helpdesk"
import { sessionUser } from "@/data/session"
import { statusLabel, threadFromTicket } from "@/utils/helpdesk"
import { goBackOrHome } from "@/utils/navigation"

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const __ = inject("$translate")
const dayjs = inject("$dayjs")

const reply = ref("")
const ticket = computed(() => ticketDetail.data)
const viewer = computed(() => sessionUser())
const thread = computed(() => threadFromTicket(ticket.value, viewer.value))
const isResolved = computed(() =>
	["resolved", "closed"].includes(String(ticket.value?.status || "").toLowerCase())
)

const metaCells = computed(() => [
	{ k: __("Raised by"), v: ticket.value?.raised_by_name || ticket.value?.raised_by || "—" },
	{ k: __("Ticket"), v: ticket.value?.name || props.id },
	{ k: __("Priority"), v: ticket.value?.priority || "—" },
	{ k: __("Agent"), v: ticket.value?.assigned_to_name || __("Unassigned") },
])

function formatWhen(value) {
	return value ? dayjs(value).format("D MMM, HH:mm") : ""
}

function load() {
	console.info("[TicketDetail] open", props.id)
	ticketDetail.fetch({ name: props.id })
}
watch(() => props.id, load, { immediate: true })

function goBack() {
	goBackOrHome(router)
}

async function send() {
	const message = reply.value.trim()
	if (!message) return
	try {
		await replyToTicket.submit({ name: props.id, message })
		console.info("[TicketDetail] reply sent on", props.id)
		reply.value = ""
		load()
		myTickets.reload?.()
	} catch (error) {
		console.warn("[TicketDetail] reply failed:", error?.messages?.[0] || error)
	}
}
</script>
