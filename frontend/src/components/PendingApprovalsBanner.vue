<template>
	<!-- Approvals surfaced where approvers work. The entry under Profile stays
	     the durable path; this banner is the visibility layer — same primitive
	     as CheckInPanel's forgot-to-check-out strip, driven by the same fenced
	     count the Profile badge reads. Renders nothing for non-approvers.
	     §12 calls for a banner here "if unresolved punch"; this is that slot.
	     GBanner is the §10.1 #10 primitive — info variant, since the state is
	     actionable rather than wrong. -->
	<GBanner
		v-if="count > 0"
		variant="info"
		interactive
		class="g-approvals"
		@click="router.push({ name: 'RemoteApprovals' })"
	>
		<!-- "{0} remote check-in(s) awaiting your approval" + "Tap to review
		     and decide." was 11 words for one count and one tap. GBanner is
		     already `interactive`, so the instruction is redundant to a
		     sighted user and noise to a screen reader, which announces the
		     row as a button regardless.
		     "remote" is NOT part of that trim, and the first attempt at this
		     cut it: the count is remote_checkin.get_pending_count and the row
		     routes to RemoteApprovals only, so an approver reading a bare
		     "check-in(s) to approve" could take it for every pending approval
		     and stop looking. A qualifier that makes the count true is
		     information, not prose. Five words, still half of eleven. -->
		<span class="g-approvals__title">
			{{ __("{0} remote check-in(s) to approve", [count]) }}
		</span>
	</GBanner>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted } from "vue"
import { useRouter } from "vue-router"

import GBanner from "@/components/glass/GBanner.vue"

import { pendingCountResource } from "@/data/remoteCheckin"

const __ = inject("$translate")
const router = useRouter()
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
