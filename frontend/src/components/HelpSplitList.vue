<!--
  HelpSplitList — one Help list, the same on the HR and IT sides (alpha.5).

  Open first: an "Open" eyebrow and the first five open rows, then a
  "See all (N)" row that opens every open row in a sheet. Finished rows sit
  behind ONE "Closed" row with its count. Sheets page 20 at a time.
  The split and the second line are pure (utils/helpdesk.js splitHelp,
  helpRowMeta, pinned by utils/__tests__/helpSplit.test.js).

  Props:
    rows        array — the list's rows (issues or tickets)
    loading     boolean — first load in flight
    title       function(row) → the row's label
    chipLabel   function(status) → the status chip's words
    emptyBody   string — what to do when nothing is open
  Emits: open(row)
-->
<template>
	<div class="flex flex-col gap-2.5">
		<span class="g-eyebrow mt-1">{{ __("Open") }}</span>
		<GListPanel v-if="loading || split.open.length" :loading="loading">
			<GListRow
				v-for="row in firstOpen"
				:key="row.name"
				:label="title(row)"
				:sublabel="helpRowMeta(row, meta)"
				@click="$emit('open', row)"
			>
				<template #badge>
					<GStatusChip :status="row.status" :label="chipLabel(row.status)" />
				</template>
			</GListRow>
			<GListRow
				v-if="split.open.length > firstOpen.length"
				:label="__('See all ({0})', [split.open.length])"
				@click="show('open')"
			/>
		</GListPanel>
		<GEmptyState v-else :title="__('Nothing open')" :body="emptyBody" />

		<GListPanel v-if="!loading && split.done.length">
			<GListRow :label="__('Closed')" :amount="String(split.done.length)" @click="show('done')" />
		</GListPanel>

		<GModal
			:is-open="sheet === 'open'"
			:title="__('Open')"
			@did-dismiss="sheet = null"
		>
			<GListPanel>
				<GListRow
					v-for="row in paged(split.open)"
					:key="row.name"
					:label="title(row)"
					:sublabel="helpRowMeta(row, meta)"
					@click="pick(row)"
				>
					<template #badge>
						<GStatusChip :status="row.status" :label="chipLabel(row.status)" />
					</template>
				</GListRow>
			</GListPanel>
			<button
				v-if="split.open.length > shown"
				type="button"
				class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
				@click="shown += PAGE"
			>
				{{ __("Show more") }}
			</button>
		</GModal>

		<GModal
			:is-open="sheet === 'done'"
			:title="__('Closed')"
			@did-dismiss="sheet = null"
		>
			<GListPanel>
				<GListRow
					v-for="row in paged(split.done)"
					:key="row.name"
					:label="title(row)"
					:sublabel="helpRowMeta(row, meta)"
					@click="pick(row)"
				>
					<template #badge>
						<GStatusChip :status="row.status" :label="chipLabel(row.status)" />
					</template>
				</GListRow>
			</GListPanel>
			<button
				v-if="split.done.length > shown"
				type="button"
				class="g-focusable g-list-more w-full py-3 text-sm text-ink-600 bg-transparent border-none"
				@click="shown += PAGE"
			>
				{{ __("Show more") }}
			</button>
		</GModal>
	</div>
</template>

<script setup>
import { computed, inject, ref } from "vue"

import GEmptyState from "@/components/glass/GEmptyState.vue"
import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GModal from "@/components/glass/GModal.vue"
import GStatusChip from "@/components/glass/GStatusChip.vue"
import { helpRowMeta, splitHelp } from "@/utils/helpdesk"
import { siteTime } from "@/utils/siteTime"

const props = defineProps({
	rows: { type: Array, default: () => [] },
	loading: { type: Boolean, default: false },
	title: { type: Function, required: true },
	chipLabel: { type: Function, required: true },
	emptyBody: { type: String, required: true },
})
const emit = defineEmits(["open"])

const __ = inject("$translate")
// ceiling: pages the rows already loaded (50 issues / every ticket the API
// returns), upgrade: server paging when someone holds more than that
const PAGE = 20

const split = computed(() => splitHelp(props.rows))
const firstOpen = computed(() => split.value.open.slice(0, 5))
const meta = { day: (v) => siteTime(v).format("D MMM"), t: __ }

const sheet = ref(null)
const shown = ref(PAGE)
const paged = (list) => list.slice(0, shown.value)

function show(which) {
	console.info("[HelpSplitList] sheet", which, "open", split.value.open.length, "done", split.value.done.length)
	shown.value = PAGE
	sheet.value = which
}

// close the sheet first: the router guard only closes PRESENTED sheets
function pick(row) {
	sheet.value = null
	emit("open", row)
}
</script>
