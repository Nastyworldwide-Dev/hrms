<template>
	<HRIssueBoard v-if="isHR" />
	<IssueList v-else />
</template>

<script setup>
import { computed } from "vue"

import { userResource } from "@/data/user"
import { hasHRRole } from "@/utils/issueBoard"
import HRIssueBoard from "./HRIssueBoard.vue"
import IssueList from "./IssueList.vue"

// one Issues tab for everyone: HR roles work the board, staff see their own
// tickets. Server-side row scope is what actually protects the data — this
// switch is presentation only.
const isHR = computed(() => hasHRRole(userResource.data?.roles))
</script>
