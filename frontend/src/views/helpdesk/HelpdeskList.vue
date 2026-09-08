<template>
	<BaseLayout :pageTitle="__('Helpdesk')">
		<template #body>
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full lg:p-7 max-w-content-column-lg mx-auto"
			>
				<ResourceError :resource="myTickets" what="your tickets" />

				<router-link :to="{ name: 'HelpdeskTicketNew' }" v-slot="{ navigate }">
					<GButton :label="__('Raise a ticket')" @click="navigate">
						<template #trailing>
							<FeatherIcon name="arrow-right" class="h-[17px] w-[17px]" aria-hidden="true" />
						</template>
					</GButton>
				</router-link>

				<!-- chips bucket by what the employee has to do (utils/helpdesk.js) -->
				<div
					class="flex flex-row gap-2 overflow-x-auto"
					role="group"
					:aria-label="__('Filter tickets')"
				>
					<button
						v-for="chip in CHIPS"
						:key="chip.key"
						type="button"
						class="g-focusable flex-none min-h-11 rounded-full border px-3.5 text-kra-label font-semibold"
						:class="
							activeChip === chip.key
								? 'bg-inkbase text-[var(--g-bg)] border-inkbase'
								: 'border-divider text-ink-600'
						"
						:aria-pressed="activeChip === chip.key"
						@click="activeChip = chip.key"
					>
						{{ __(chip.label) }}
					</button>
				</div>

				<span class="g-eyebrow mt-1">{{ __("Tickets") }}</span>
				<div class="flex flex-col gap-2.5">
					<!-- ONE panel for the whole list (§15.1), exactly as Issues does -->
					<GListPanel
						v-if="myTickets.loading || rows.length"
						:loading="myTickets.loading && !myTickets.data"
					>
						<GListRow
							v-for="ticket in rows"
							:key="ticket.name"
							:label="ticket.subject || ticket.name"
							:sublabel="ticketMeta(ticket)"
							@click="router.push({ name: 'HelpdeskTicketDetail', params: { id: ticket.name } })"
						>
							<template #badge>
								<GStatusChip :status="ticket.status" :label="__(statusLabel(ticket.status))" />
							</template>
						</GListRow>
					</GListPanel>

					<GEmptyState
						v-if="!myTickets.loading && !rows.length"
						:title="activeChip === 'all' ? __('No tickets yet') : __('Nothing here')"
						:body="
							activeChip === 'all'
								? __(
										'Laptop, access, email or admin trouble? Raise a ticket and the Helpdesk team will pick it up.'
								  )
								: __('No tickets match this filter.')
						"
					/>
				</div>

				<span class="text-caption text-ink-600">
					{{
						__(
							"IT & admin tickets are handled by the Helpdesk team. Tap a ticket to read replies."
						)
					}}
				</span>
			</div>
		</template>
	</BaseLayout>
</template>

<script setup>
import GListRow from "@/components/glass/GListRow.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import GButton from "@/components/glass/GButton.vue"
import { FeatherIcon } from "frappe-ui"
import { useRouter } from "vue-router"
import { computed, inject, onMounted, ref } from "vue"

import BaseLayout from "@/components/BaseLayout.vue"
import ResourceError from "@/components/ResourceError.vue"
import { myTickets } from "@/data/helpdesk"
import { CHIPS, filterTickets, statusLabel } from "@/utils/helpdesk"

const router = useRouter()
const __ = inject("$translate")
const dayjs = inject("$dayjs")

const activeChip = ref("all")
const rows = computed(() => filterTickets(myTickets.data, activeChip.value))

// __("All"), __("Open"), __("Awaiting you"), __("Resolved")

// The HRM shows WHO raised it (HR request 2026-09-08): an employee sees their
// own name, an HR user or agent sees the raiser of every ticket they can read.
function ticketMeta(ticket) {
	const when = ticket.modified ? dayjs(ticket.modified).format("D MMM, HH:mm") : ""
	const who = ticket.raised_by_name ? `${__("by")} ${ticket.raised_by_name}` : ""
	return [ticket.name, ticket.ticket_type, who, when].filter(Boolean).join(" · ")
}

onMounted(() => {
	console.info("[HelpdeskList] opened")
	myTickets.fetch()
})
</script>
