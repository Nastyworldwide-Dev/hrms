<template>
	<GPage>
		<!-- The one header (alpha.5); the ticket's status sits where the bell
		     and avatar would. -->
		<ShellHeader :title="ticket?.subject || props.id">
			<template v-if="ticket?.status" #actions>
				<GStatusChip
					class="flex-none"
					:status="ticket.status"
					:label="__(statusLabel(ticket.status))"
				/>
			</template>
		</ShellHeader>
		<ion-content class="g-page__content">
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full lg:py-7 max-w-content-column-lg mx-auto"
			>
				<ResourceError :resource="ticketDetail" back what="this ticket" />
				<GSkeleton v-if="ticketDetail.loading && !ticket" height="220px" />

				<template v-if="ticket">
					<!-- meta grid: ONE glass surface with hair dividers (§15.2). The
					     first cell is WHO raised it — the HRM's own addition.
					     Built by hand until 22 Sep 2026, which put .g-glass in a
					     view and hardcoded its own dividers and padding; GMetaGrid
					     owns the surface now. -->
					<GMetaGrid :cells="metaCells" />

					<span class="g-eyebrow mt-1">{{ __("Conversation") }}</span>
					<div class="flex flex-col gap-2.5">
						<GChatBubble
							v-for="m in thread"
							:key="m.id"
							:mine="m.kind === 'me'"
							:who="m.who"
							:when="formatWhen(m.when)"
						>
							<!-- Helpdesk stores rich text. Sanitised HERE as well as
							     server-side: safeHtml is the app's own allow-list, and
							     a thread is the one place a ticket's author controls
							     the markup. -->
							<div class="prose-sm" v-html="safeHtml(m.html)" />
						</GChatBubble>
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
						<!-- icon-only send, as the mockup draws it (44px target via GIconButton) -->
						<GIconButton
							type="submit"
							class="flex-none mb-1"
							:label="replyToTicket.loading ? __('Sending…') : __('Send')"
							:disabled="replyToTicket.loading || !reply.trim()"
						>
							<ArrowUp class="h-4 w-4" />
						</GIconButton>
					</form>
				</template>
			</div>
		</ion-content>
	</GPage>
</template>

<script setup>
import { safeHtml } from "@/utils/safeHtml"
import { ArrowUp } from "lucide-vue-next"
import ShellHeader from "@/components/ShellHeader.vue"
import GPage from "@/components/glass/GPage.vue"
import GIconButton from "@/components/glass/GIconButton.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GSkeleton from "@/components/glass/GSkeleton.vue"
import GMetaGrid from "@/components/glass/GMetaGrid.vue"
import GChatBubble from "@/components/glass/GChatBubble.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GTextarea from "@/components/glass/GTextarea.vue"
import { IonContent } from "@ionic/vue"

import { computed, inject, ref, watch } from "vue"

import ResourceError from "@/components/ResourceError.vue"
import { myTickets, replyToTicket, ticketDetail } from "@/data/helpdesk"
import { sessionUser } from "@/data/session"
import { statusLabel, threadFromTicket } from "@/utils/helpdesk"

const props = defineProps({ id: { type: String, required: true } })
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
