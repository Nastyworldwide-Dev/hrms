<template>
	<BaseLayout :pageTitle="__('Approvals')">
		<template #body>
			<!-- Everything waiting on YOUR decision, oldest first (audit-flows 4B;
			     owner ruling 23 Sep: approvals appear only where they can be done).
			     Every row opens the same request sheet that decides it, so there is
			     one way to approve and one way to say no (with a reason). -->
			<GPullRefresh @refresh="refresh" />
			<div
				class="flex flex-col gap-4 px-4 pt-6 pb-8 w-full max-w-content-column-lg mx-auto lg:p-7"
			>
				<ResourceError :resource="waiting" what="your approvals" />

				<GListPanel v-if="waiting.loading && !rows.length" loading />

				<template v-else-if="!waiting.error">
					<p v-if="rows.length" class="text-card-title text-ink-600">
						{{ summary }}
					</p>
					<GListPanel v-if="rows.length">
						<GListRow
							v-for="row in rows"
							:key="`${row.doctype}:${row.name}`"
							:label="`${__(row.kind)} · ${row.who}`"
							:sublabel="rowLine(row)"
							@click="open(row)"
						/>
					</GListPanel>
					<p v-else class="text-card-title text-ink-600">{{ __("Nothing is waiting on you.") }}</p>
					<p v-if="waiting.data?.capped" class="text-caption text-ink-600">
						{{ __("Showing the oldest first. More are waiting.") }}
					</p>
				</template>
			</div>

			<GModal :is-open="!!selected" @did-dismiss="close">
				<RequestActionSheet
					v-if="selected"
					:fields="REQUEST_SUMMARY_FIELDS[selected.doctype]"
					v-model="selected"
				/>
			</GModal>
		</template>
	</BaseLayout>
</template>

<script setup>
import { computed, inject, ref } from "vue"
import { createResource } from "frappe-ui"

import BaseLayout from "@/components/BaseLayout.vue"
import RequestActionSheet from "@/components/RequestActionSheet.vue"
import ResourceError from "@/components/ResourceError.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import GPullRefresh from "@/components/glass/GPullRefresh.vue"
import { REQUEST_SUMMARY_FIELDS } from "@/data/config/requestSummaryFields"

const __ = inject("$translate")
const $dayjs = inject("$dayjs")

// The server decides who sees what: only requests routed to the caller, by the
// same check approval.decide uses (hrms/api/approvals_list.py).
const waiting = createResource({
	url: "hrms.api.approvals_list.get_waiting_for_me",
	auto: true,
})
const rows = computed(() => waiting.data?.rows || [])

//: "3 waiting · oldest since 20 Sep" (mockup 4's summary line).
const summary = computed(() => {
	const oldest = rows.value[0]?.modified
	const count = __("{0} waiting", [rows.value.length])
	return oldest ? `${count} · ${__("oldest since {0}", [$dayjs(oldest).format("D MMM")])}` : count
})

function rowLine(row) {
	return [row.when, row.detail].filter(Boolean).join(" · ")
}

const selected = ref(null)
function open(row) {
	console.info("[Approvals] opening", row.doctype)
	selected.value = { doctype: row.doctype, name: row.name }
}
function close() {
	selected.value = null
	// A decision made in the sheet changes the queue.
	waiting.reload()
}

async function refresh(event) {
	console.info("[Approvals] pull-to-refresh")
	await waiting.reload()
	event.target?.complete?.()
}
</script>
