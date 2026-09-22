<!--
  NeedsYou — everything waiting on this employee, in one place (2.0 slice 1.3,
  UX_PLAN §3.1 "Needs you").

  It replaces `PendingApprovalsBanner`, which answered one question — "you have
  remote check-ins to approve" — with its own conditional banner. The plan's
  row is wider than that: approvals, geofence reviews, issue replies, and later
  SOPs to read and certificates expiring. As banners, each new kind would be
  another conditional block above the fold, each with its own empty state,
  each competing for the same attention. As rows in one bounded list, a new
  kind is a row.

  WHAT IT IS NOT: a notification list. A notification says something HAPPENED;
  these rows say something is WAITING, and every one of them is an action this
  employee can take. The bell stays where it is.

  ABSENCE IS THE EMPTY STATE. §11 asks every block to have one, and for this
  block the right one is rendering nothing. A permanent "nothing needs you" row
  is a row that is wrong most of the time and costs the fold every day.

  BOUNDED at three, the same shape the request panel uses — three rows and
  "N more" — because a list that needs you is exactly the list that can spike.
-->
<template>
	<div v-if="rows.length" class="w-full">
		<div class="g-eyebrow mb-4">{{ __("Needs you") }}</div>
		<GListPanel>
			<GListRow
				v-for="row in shown"
				:key="row.key"
				:label="row.label"
				:sublabel="row.sublabel"
				@click="row.go()"
			>
				<template #icon>
					<component :is="row.icon" class="g-row-icon" />
				</template>
			</GListRow>
		</GListPanel>
		<!-- Not a GGhostButton: that is a glass surface, and this block already
		     spends one on its panel (§15.1). A text control under a list costs
		     none — the same decision the request panel's "Show N more" made. -->
		<button
			v-if="hidden > 0"
			type="button"
			class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
			@click="showAll = true"
		>
			{{ __("Show {0} more", [hidden]) }}
		</button>
		<!-- The count changes without the employee doing anything — a socket
		     event, a colleague submitting. A polite region says so; `role=alert`
		     would interrupt whatever is being read. -->
		<p class="sr-only" role="status">{{ announcement }}</p>
	</div>
</template>

<script setup>
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue"
import { useRouter } from "vue-router"
import { CircleCheckBig } from "lucide-vue-next"

import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"

import { pendingCountResource } from "@/data/remoteCheckin"

const __ = inject("$translate")
const router = useRouter()
const socket = inject("$socket")

//: Three, then "N more" — the request panel's bound, for the same reason: this
//: is the list that spikes when somebody goes on leave and their approvals
//: pile up.
const HOME_ROWS = 3
const showAll = ref(false)

const approvals = computed(() => Number(pendingCountResource.data) || 0)

//: Every kind of waiting thing, in one list. Adding a kind is adding an entry
//: here; it does not change this component's shape or Home's.
const rows = computed(() => {
	const out = []
	if (approvals.value > 0) {
		out.push({
			key: "remote-checkin",
			icon: CircleCheckBig,
			// "remote" is load-bearing and an earlier trim of this copy removed
			// it: the count is `remote_checkin.get_pending_count` and the row
			// goes to RemoteApprovals only, so a bare "check-ins to approve"
			// could be read as EVERY pending approval and an approver would
			// stop looking. A qualifier that makes a count true is information.
			label: __("{0} remote check-in(s) to approve", [approvals.value]),
			sublabel: null,
			go: () => router.push({ name: "RemoteApprovals" }),
		})
	}
	return out
})

const shown = computed(() => (showAll.value ? rows.value : rows.value.slice(0, HOME_ROWS)))
const hidden = computed(() => (showAll.value ? 0 : Math.max(0, rows.value.length - HOME_ROWS)))

const announcement = computed(() =>
	rows.value.length ? __("{0} thing(s) need you", [rows.value.length]) : ""
)

const onRealtime = () => pendingCountResource.reload()

onMounted(() => {
	pendingCountResource.fetch()
	socket?.on?.("hrms:remote_checkin_request", onRealtime)
})

onBeforeUnmount(() => {
	socket?.off?.("hrms:remote_checkin_request", onRealtime)
})
</script>
