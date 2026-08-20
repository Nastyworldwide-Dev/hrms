<!--
  Quick-link list — §12's Home anatomy, "quick-link list (4 rows)".
  Composes GListPanel + GListRow, so the panel and its rows are ONE glass
  surface (§15.1), not one per row.
  Behaviour is unchanged: same items prop, same named routes, same order.
-->
<template>
	<div class="w-full">
		<div class="g-quicklinks__title">{{ title || __("Quick Links") }}</div>

		<GListPanel :loading="loading" :rows="4" :empty="!loading && !props.items.length">
			<template #empty>
				<GEmptyState
					:title="__('Nothing to do here yet')"
					:body="__('Shortcuts to the things you use most will appear here')"
				/>
			</template>

			<GListRow
				v-for="link in props.items"
				:key="link.title"
				:label="link.title"
				@click="router.push({ name: link.route })"
			>
				<template #icon>
					<component :is="link.icon" class="h-[18px] w-[18px]" />
				</template>
			</GListRow>
		</GListPanel>
	</div>
</template>

<script setup>
import { inject } from "vue"
import { useRouter } from "vue-router"

import GListPanel from "@/components/glass/GListPanel.vue"
import GListRow from "@/components/glass/GListRow.vue"
import GEmptyState from "@/components/glass/GEmptyState.vue"

const __ = inject("$translate")
const router = useRouter()

const props = defineProps({
	items: {
		type: Array,
		required: true,
	},
	title: {
		type: String,
		required: false,
		default: "",
	},
	// §11.2: skeleton rows while the caller resolves its links, never a spinner
	loading: {
		type: Boolean,
		default: false,
	},
})
</script>

<style scoped>
.g-quicklinks__title {
	margin-bottom: 10px;
	font-family: var(--g-type-eyebrow-family);
	font-size: var(--g-type-eyebrow-size);
	font-weight: var(--g-type-eyebrow-weight);
	letter-spacing: var(--g-type-eyebrow-tracking);
	text-transform: uppercase;
	color: var(--g-ink2);
}
</style>
