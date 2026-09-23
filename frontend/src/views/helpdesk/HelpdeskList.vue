<template>
	<!-- body only: the page chrome (header, HR / IT pills, Who to ask and the
	     one "New ticket" button) belongs to HelpdeskHub.vue -->
	<div class="flex flex-col gap-4 px-4 pt-4 w-full lg:px-7 max-w-content-column-lg mx-auto">
		<ResourceError :resource="myTickets" what="your IT tickets" />
		<HelpSplitList
			:rows="myTickets.data || []"
			:loading="myTickets.loading && !myTickets.data"
			:title="(ticket) => ticket.subject || __('Ticket')"
			:chip-label="(status) => __(statusLabel(status))"
			:empty-body="__('Laptop, access or email trouble? Tap New ticket below.')"
			@open="openTicket"
		/>
	</div>
</template>

<script setup>
import { useRouter } from "vue-router"
import { inject, onMounted } from "vue"

import HelpSplitList from "@/components/HelpSplitList.vue"
import ResourceError from "@/components/ResourceError.vue"
import { myTickets } from "@/data/helpdesk"
import { statusLabel } from "@/utils/helpdesk"

const router = useRouter()
const __ = inject("$translate")

function openTicket(ticket) {
	console.info("[HelpdeskList] open ticket", ticket.name)
	router.push({ name: "HelpdeskTicketDetail", params: { id: ticket.name } })
}

onMounted(() => {
	console.info("[HelpdeskList] opened")
	myTickets.fetch()
})
</script>
