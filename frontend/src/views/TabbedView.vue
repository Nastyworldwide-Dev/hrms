<template>
	<ion-page>
		<div class="flex h-full w-full">
			<SideNav />
			<div class="relative flex-1 min-w-0">
				<ion-tabs>
					<ion-router-outlet></ion-router-outlet>
					<BottomTabs />
				</ion-tabs>
			</div>
		</div>
	</ion-page>
</template>

<script setup>
import { IonTabs, IonPage, IonRouterOutlet } from "@ionic/vue"
import BottomTabs from "@/components/BottomTabs.vue"
import SideNav from "@/components/SideNav.vue"
</script>
