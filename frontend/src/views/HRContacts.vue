<template>
	<ion-page>
		<ion-content class="ion-padding">
			<div class="flex flex-col h-screen w-screen">
				<div class="w-full sm:w-96">
					<header
						class="flex flex-row bg-white shadow-sm py-4 px-3 items-center justify-between border-b sticky top-0 z-10"
					>
						<div class="flex flex-row items-center">
							<Button
								variant="ghost"
								class="!pl-0 hover:bg-white"
								@click="router.back()"
							>
								<FeatherIcon name="chevron-left" class="h-5 w-5" />
							</Button>
							<h2 class="text-xl font-semibold text-gray-900">
								{{ __("HR Contacts") }}
							</h2>
						</div>
						<Button
							variant="ghost"
							class="hover:bg-white"
							@click="reload"
							:loading="hrContacts.loading"
						>
							<FeatherIcon name="refresh-cw" class="h-4 w-4" />
						</Button>
					</header>

					<div class="flex flex-col mt-3 p-3 gap-3">
						<!-- Loading state -->
						<div v-if="hrContacts.loading && !hrContacts.data" class="space-y-3">
							<div
								v-for="i in 3"
								:key="i"
								class="h-24 bg-gray-100 animate-pulse rounded-md"
							/>
						</div>

						<!-- Empty state -->
						<div
							v-else-if="!hrContacts.data || hrContacts.data.length === 0"
							class="flex flex-col items-center justify-center py-16 px-6 text-center"
						>
							<div
								class="h-16 w-16 rounded-full bg-gray-100 flex items-center justify-center mb-3"
							>
								<FeatherIcon name="users" class="h-7 w-7 text-gray-400" />
							</div>
							<div class="text-sm font-medium text-gray-700">
								{{ __("No HR contacts available") }}
							</div>
							<div class="text-xs text-gray-500 mt-1">
								{{
									__(
										"Ask your administrator to assign the HR Manager or HR User role to your HR team."
									)
								}}
							</div>
						</div>

						<!-- Cards -->
						<ContactCard
							v-else
							v-for="contact in hrContacts.data"
							:key="contact.name"
							:contact="contact"
						/>
					</div>
				</div>
			</div>
		</ion-content>
	</ion-page>
</template>

<script setup>
import { inject, onMounted } from "vue"
import { useRouter } from "vue-router"
import { IonPage, IonContent } from "@ionic/vue"
import { FeatherIcon, Button } from "frappe-ui"

import ContactCard from "@/components/ContactCard.vue"
import { hrContactsResource } from "@/data/hrContacts"

const __ = inject("$translate")
const router = useRouter()
const hrContacts = hrContactsResource

onMounted(() => {
	if (!hrContacts.data) hrContacts.fetch()
})

const reload = () => hrContacts.reload()
</script>
