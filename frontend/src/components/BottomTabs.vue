<template>
	<!-- ion-tab-bar is retained, not replaced: Ionic's per-tab navigation stacks
	     live in this component, and rebuilding it would lose them. Everything
	     below is a restyle of the HOST plus its published custom properties. -->
	<!-- Scroll-edge fade: content dissolves into the page ground before it
	     reaches the floating bar, so rows never butt against the glass. -->
	<div class="g-tabbar-fade lg:hidden" aria-hidden="true" />
	<ion-tab-bar slot="bottom" class="g-tabbar lg:hidden">
		<!-- The iOS 26 lens (alpha.8): ONE pill behind the tabs that slides to
		     the chosen one, inset inside its cell. Decorative; the tab itself
		     says it is selected. -->
		<span class="g-tabbar__lens" :style="lensStyle" aria-hidden="true" />
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.route"
			:tab="item.route"
			:href="item.route"
			class="g-tabbar__btn"
		>
			<!-- 19×19 icon slot. No container behind the active item (#14): the
			     selected tab is carried by the icon (full ink) + bold label, not a
			     well/capsule — the bar is one continuous glass material. -->
			<span class="g-tabbar__well" :class="{ 'g-tabbar__well--active': isActive(item) }">
				<component :is="item.icon" class="h-icon-md w-icon-md flex-none" />
			</span>
			<span class="g-tabbar__label" :class="{ 'g-tabbar__label--active': isActive(item) }">{{
				item.shortTitle
			}}</span>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import { computed, inject } from "vue"

import { TAB_ITEMS } from "@/data/navItems"

const __ = inject("$translate")

const route = useRoute()

const tabItems = TAB_ITEMS.map((item) => ({
	...item,
	shortTitle: __(item.shortTitle),
}))

// More claims its child routes (`routes`) so the indicator stays lit on them
const isActive = (item) =>
	item.routes ? item.routes.some((path) => route.path.startsWith(path)) : route.path === item.route

//: The lens sits on the active tab's cell: tabs share the bar equally, so its
//: position is the tab's index (moved with transform, so it can slide).
const lensStyle = computed(() => {
	const at = tabItems.findIndex(isActive)
	const n = tabItems.length
	// The row of tabs spans the bar minus its 4 pt padding each side; one
	// cell is that / n. The lens is a cell minus 4 pt each side and steps a
	// whole cell per tab (measured centred to 0.1 pt, WebKit).
	// The lens box is exactly one tab cell wide (the tabs share the bar
	// equally) and placed by `left` on the same arithmetic as the cells, so
	// it lands on sub-pixels exactly as the tabs do. A translateX(400%) was
	// rounded to whole pixels by WebKit and drifted 1.6 pt by the 5th tab.
	const cell = `(100% - 8px) / ${n}`
	return {
		width: `calc(${cell})`,
		left: `calc(4px + ${Math.max(at, 0)} * ${cell})`,
		opacity: at < 0 ? 0 : 1,
	}


})
</script>

<style scoped>
/* ion-tab-bar/-button are shadow DOM: Tailwind text classes on the host never
   reach the inner button, whose colour comes from --color/--color-selected —
   slotted content (icon stroke + label) inherits it. height:auto lifts Ionic's
   fixed 50px bar so nothing clips, and contain:content keeps the rounded
   corners from being painted over. BOTH are retained from the Modernist
   implementation; they are the reason this component works at all.

   The floating pill is achieved on the HOST element, which is light DOM and
   therefore ours to position — see the glass rule in glass-components.css. */
ion-tab-bar.g-tabbar {
	height: auto;
	contain: content;
	--border: 0;
	/* transparent inner background so the host's own glass shows through */
	--background: transparent;
}
ion-tab-button.g-tabbar__btn {
	--color: var(--g-ink3);
	--color-selected: var(--g-accent-ink);
	--background: transparent;
	--background-focused: transparent;
	--ripple-color: transparent;
	--padding-start: 0;
	--padding-end: 0;
	--padding-top: 0;
	--padding-bottom: 0;
}
/* Icon and label centred inside the tab, so the selected pill holds them with
   even space above and below (owner, 25 Sep 2026: the icon touched the pill's
   top edge; measured icon top = pill top). */
ion-tab-button.g-tabbar__btn::part(native) {
	justify-content: center;
	gap: 2px;
}
</style>
