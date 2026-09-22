<!--
  Quick-link tiles — §12's Home anatomy slot, now a grid instead of a list.

  WHY IT CHANGED: Home passes SEVEN links (Home.vue's baseQuickLinks is six plus
  one unconditional HR row). As GListRows that is 7 x 50px = ~350px, on a phone
  whose whole usable height is about 440px (invariant F1,
  src/views/__tests__/home-fold-budget.test.js) — one panel taking four fifths of
  the screen to show seven two-word labels in rows 320px wide.
  Four across is two rows: ~120px with one-line labels, ~145px when they wrap.
  A saving of roughly 206px measured against the wrapped worst case.
  (An earlier draft of this comment said eight links and 450px. Both were
  guessed rather than counted; the arithmetic above is from the tokens.)

  SURFACE BUDGET: still ONE surface (§15.1). GTileGrid owns the .g-glass and the
  tiles are its cells — N glass cards under v-for would be N surfaces at
  runtime, and §15 allows six per screen.

  Behaviour is unchanged: same items prop, same named routes, same query, same
  order, same loading and empty states.
-->
<template>
	<div class="w-full">
		<div class="g-eyebrow mb-2.5">{{ title || __("Quick Links") }}</div>

		<GTileGrid :loading="loading" :empty="!loading && !props.items.length">
			<template #empty>
				<GEmptyState
					:title="__('Nothing to do here yet')"
					:body="__('Shortcuts to the things you use most will appear here')"
				/>
			</template>

			<!-- A real <button>: the whole tile is the target, it is reachable by
			     keyboard and it announces as a button. GListRow gave that for
			     free and the grid must not quietly lose it (WCAG 2.1.1, 2.5.8).
			     v-for sits on this element and nothing else does — no v-else
			     beside it, since Vue 3 resolves v-if first on one element. -->
			<button
				v-for="link in props.items"
				:key="link.title"
				type="button"
				class="g-cell g-cell--quick"
				@click="router.push({ name: link.route, query: link.query })"
			>
				<component :is="link.icon" class="h-5 w-5" aria-hidden="true" />
				<span class="g-cell__label">{{ link.title }}</span>
			</button>
		</GTileGrid>
	</div>
</template>

<script setup>
import { inject } from "vue"
import { useRouter } from "vue-router"

import GEmptyState from "@/components/glass/GEmptyState.vue"
import GTileGrid from "@/components/glass/GTileGrid.vue"

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
	// §11.2: skeleton tiles while the caller resolves its links, never a spinner
	loading: {
		type: Boolean,
		default: false,
	},
})
</script>

<!--
	.g-quicklinks__title used to live here: five of the six eyebrow tokens copied
	by hand, with the sixth — the colour — set to --ink2 instead of --accent-ink.
	It read as an eyebrow in source and rendered grey next to olive section
	headers on the same screen. §10's eyebrow is the treatment; a component does
	not get its own copy of it.
-->
