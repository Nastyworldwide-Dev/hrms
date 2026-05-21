app_name = "nsty"
app_title = "Nsty"
app_publisher = "Nsty"
app_description = "Nsty HRMS extensions — Malaysian statutory, OT, deductions."
app_email = "dev@example.com"
app_license = "MIT"
app_version = "0.0.1"

override_doctype_class = {
	"Employee Checkin": "nsty.overrides.employee_checkin.CustomEmployeeCheckin",
}

doc_events = {
	"Employee": {
		"after_save": "nsty.doc_events.employee.sync_hrms_only_user_permission",
	},
}

fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["name", "in", ["Employee-restrict_user_permission_to_hrms"]]],
	},
]
