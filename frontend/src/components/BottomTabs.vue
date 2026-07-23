<template>
	<ion-tab-bar
		slot="bottom"
		class="bg-ground border-t-2 border-divider standalone:pb-safe-bottom lg:hidden"
	>
		<ion-tab-button
			v-for="item in tabItems"
			:key="item.title"
			:tab="item.title"
			:href="item.route"
			:class="[
				'relative bg-ground pt-2 pb-3 space-y-1 transition active:scale-95',
				route.path === item.route ? 'text-inkbase' : 'text-ink-500',
			]"
		>
			<span
				class="absolute top-0 inset-x-0 h-[3px]"
				:class="route.path === item.route ? 'bg-accent' : 'bg-transparent'"
			></span>
			<component :is="item.icon" class="h-5 w-5" />
			<div class="text-[9px] uppercase font-extrabold tracking-[0.08em]">
				{{ item.title }}
			</div>
		</ion-tab-button>
	</ion-tab-bar>
</template>

<script setup>
import { useRoute } from "vue-router"

import { IonTabBar, IonTabButton } from "@ionic/vue"

import { inject } from "vue"

import { NAV_ITEMS } from "@/data/navItems"

const __ = inject("$translate")

const route = useRoute()

const tabItems = NAV_ITEMS.map((item) => ({ ...item, title: __(item.title) }))
</script>
