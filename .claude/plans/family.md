CLASS: an awaited resource read in a lifecycle hook rethrows a failure the screen already drew and the seam already reported, so Vue logs a render crash
frontend/src/components/FormView.vue onMounted same-root — fixed: catch the read, stop start-up when it failed
other views awaiting .promise not-affected — grep of frontend/src/views for get.promise / .get.fetch() found none
