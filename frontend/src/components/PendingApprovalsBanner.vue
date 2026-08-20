<template>
	<!-- Approvals surfaced where approvers work. The entry under Profile stays
	     the durable path; this banner is the visibility layer — same primitive
	     as CheckInPanel's forgot-to-check-out strip, driven by the same fenced
	     count the Profile badge reads. Renders nothing for non-approvers. -->
	<router-link
		v-if="count > 0"
		:to="{ name: 'RemoteApprovals' }"
		class="flex flex-row items-center gap-3 border border-accent border-l-4 bg-accent-100 px-3 py-2.5 cursor-pointer"
	>
		<FeatherIcon name="check-square" class="h-4 w-4 shrink-0 text-accent-800" />
		<div class="flex flex-col flex-1 min-w-0 gap-0.5">
			<div class="text-card-title font-semibold text-accent-800">
				{{ __("{0} remote check-in(s) awaiting your approval", [count]) }}
			</div>
			<div class="text-kra-label text-accent-800/80">
				{{ __("Tap to review and decide.") }}
			</div>
		</div>
		<span
			class="inline-flex bg-accent text-ground text-caption font-sans font-extrabold px-1.5 py-0.5"
		>
			{{ __("Review") }}
		</span>
	</router-link>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted } from "vue"
import { FeatherIcon } from "frappe-ui"

import { pendingCountResource } from "@/data/remoteCheckin"

const __ = inject("$translate")
const socket = inject("$socket")

const count = computed(() => Number(pendingCountResource.data) || 0)

const onRealtime = () => pendingCountResource.reload()

onMounted(() => {
	pendingCountResource.fetch()
	socket?.on?.("hrms:remote_checkin_request", onRealtime)
})

onBeforeUnmount(() => {
	socket?.off?.("hrms:remote_checkin_request", onRealtime)
})
</script>
