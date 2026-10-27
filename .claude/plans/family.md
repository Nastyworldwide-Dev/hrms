CLASS: SOP folder controls that refuse without saying why, or refuse a valid folder
hrms/api/sop.py save_folder/delete_folder same-root — existing folder looked up by name (_folder_ref), only a new name capped at 80
hrms/api/sop.py move_folder not-affected — checks the name against the folder list, no length cap
frontend/src/views/sop/SopManageFolders.vue same-root — rename Save says why it is dimmed; moves stay focusable; Delete 44px
frontend/src/views/sop/SopFormSheet.vue same-root — one No folder choice; cancelled New folder puts the choice back; Enter creates
frontend/src/components/glass/GIconButton.vue same-root — a disabled icon button looks unavailable (.g-iconbtn:disabled)
