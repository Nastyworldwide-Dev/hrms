frappe.provide("hrms");

$.extend(hrms, {
	proceed_save_with_reminders_frequency_change: () => {
		frappe.ui.hide_open_dialog();
		frappe.call({
			method: "hrms.hr.doctype.hr_settings.hr_settings.set_proceed_with_frequency_change",
			callback: () => {
				// nosemgrep: frappe-semgrep-rules.rules.frappe-cur-frm-usage
				cur_frm.save();
			},
		});
	},

	set_payroll_frequency_to_null: (frm) => {
		if (cint(frm.doc.salary_slip_based_on_timesheet)) {
			frm.set_value("payroll_frequency", "");
		}
	},

	get_current_employee: async (frm) => {
		const employee = (
			await frappe.db.get_value("Employee", { user_id: frappe.session.user }, "name")
		)?.message?.name;

		return employee;
	},

	validate_mandatory_fields: (frm, selected_rows, items = "Employees") => {
		const missing_fields = [];
		for (d in frm.fields_dict) {
			if (frm.fields_dict[d].df.reqd && !frm.doc[d] && d !== "__newname")
				missing_fields.push(frm.fields_dict[d].df.label);
		}

		if (missing_fields.length) {
			let message = __("Mandatory fields required for this action:");
			message += "<br><br><ul><li>" + missing_fields.join("</li><li>") + "</ul>";
			frappe.throw({
				message: message,
				title: __("Missing Fields"),
			});
		}

		if (!selected_rows.length)
			frappe.throw({
				message: __("Please select at least one row to perform this action."),
				title: __("No {0} Selected", [__(items)]),
			});
	},

	setup_employee_filter_group: (frm) => {
		const filter_wrapper = frm.fields_dict.filter_list.$wrapper;
		filter_wrapper.empty();

		frappe.model.with_doctype("Employee", () => {
			frm.filter_list = new frappe.ui.FilterGroup({
				parent: filter_wrapper,
				doctype: "Employee",
				on_change: () => {
					frm.advanced_filters = frm.filter_list
						.get_filters()
						.reduce((filters, item) => {
							// item[3] is the value from the array [doctype, fieldname, condition, value]
							if (item[3]) {
								filters.push(item.slice(1, 4));
							}
							return filters;
						}, []);
					frm.trigger("get_employees");
				},
			});
		});
	},

	render_employees_datatable: (
		frm,
		columns,
		employees,
		no_data_message = __("No Data"),
		get_editor = null,
		events = {},
	) => {
		// section automatically collapses on applying a single filter
		frm.set_df_property("quick_filters_section", "collapsible", 0);
		frm.set_df_property("advanced_filters_section", "collapsible", 0);

		if (frm.employees_datatable) {
			frm.employees_datatable.rowmanager.checkMap = [];
			frm.employees_datatable.options.noDataMessage = no_data_message;
			frm.employees_datatable.refresh(employees, columns);
			return;
		}

		const $wrapper = frm.get_field("employees_html").$wrapper;
		const employee_wrapper = $(`<div class="employee_wrapper">`).appendTo($wrapper);
		const datatable_options = {
			columns: columns,
			data: employees,
			checkboxColumn: true,
			checkedRowStatus: false,
			serialNoColumn: false,
			dynamicRowHeight: true,
			inlineFilters: true,
			layout: "fluid",
			cellHeight: 35,
			noDataMessage: no_data_message,
			disableReorderColumn: true,
			getEditor: get_editor,
			events: events,
		};
		frm.employees_datatable = new frappe.DataTable(employee_wrapper.get(0), datatable_options);
	},

	handle_realtime_bulk_action_notification: (frm, event, doctype) => {
		frappe.realtime.off(event);
		frappe.realtime.on(event, (message) => {
			hrms.notify_bulk_action_status(
				doctype,
				message.failure,
				message.success,
				message.for_processing,
			);

			// refresh only on complete/partial success
			if (message.success) frm.refresh();
		});
	},

	notify_bulk_action_status: (doctype, failure, success, for_processing = false) => {
		let action = __("create/submit");
		let action_past = __("created");
		if (for_processing) {
			action = __("process");
			action_past = __("processed");
		}

		let message = "";
		let title = __("Success");
		let indicator = "green";

		if (failure.length) {
			message += __("Failed to {0} {1} for employees:", [action, doctype]);
			message += " " + frappe.utils.comma_and(failure) + "<hr>";
			message += __(
				"Check <a href='/app/List/Error Log?reference_doctype={0}'>{1}</a> for more details",
				[doctype, __("Error Log")],
			);
			title = __("Failure");
			indicator = "red";

			if (success.length) {
				message += "<hr>";
				title = __("Partial Success");
				indicator = "orange";
			}
		}

		if (success.length) {
			message += __("Successfully {0} {1} for the following employees:", [
				action_past,
				doctype,
			]);
			message += __(
				"<table class='table table-bordered'><tr><th>{0}</th><th>{1}</th></tr>",
				[__("Employee"), doctype],
			);
			for (const d of success) {
				message += `<tr><td>${d.employee}</td><td>${d.doc}</td></tr>`;
			}
			message += "</table>";
		}

		frappe.msgprint({
			message,
			title,
			indicator,
			is_minimizable: true,
		});
	},

	// Populate an attendance-timezone picker. Mirrors how Frappe fills
	// System Settings' own time_zone Select, but through an HR-readable
	// endpoint (frappe's loader is System Manager-only).
	set_timezone_options: async (frm, fieldname) => {
		if (!hrms._timezones) {
			const { message } = await frappe.call({
				method: "hrms.api.system_settings.get_timezones",
			});
			hrms._timezones = message || [];
		}
		frm.set_df_property(fieldname, "options", [""].concat(hrms._timezones));
	},

	fetch_geolocation: async (frm) => {
		if (!navigator.geolocation) {
			frappe.msgprint({
				message: __("Geolocation is not supported by your current browser"),
				title: __("Geolocation Error"),
				indicator: "red",
			});
			hide_field(["geolocation"]);
			return;
		}

		frappe.dom.freeze(__("Fetching your geolocation") + "...");

		navigator.geolocation.getCurrentPosition(
			async (position) => {
				frappe.run_serially([
					() => frm.set_value("latitude", position.coords.latitude),
					() => frm.set_value("longitude", position.coords.longitude),
					() => frm.call("set_geolocation"),
					() => frappe.dom.unfreeze(),
				]);
			},

			(error) => {
				frappe.dom.unfreeze();

				let msg = __("Unable to retrieve your location") + "<br><br>";
				if (error) {
					msg += __("ERROR({0}): {1}", [error.code, error.message]);
				}
				frappe.msgprint({
					message: msg,
					title: __("Geolocation Error"),
					indicator: "red",
				});
			},
		);
	},

	capture_selfie: async (frm) => {
		// Selfie check-in/check-out: opens the device camera, captures a JPEG,
		// uploads via /api/method/upload_file, and sets the `selfie_image`
		// field. Mirrors the React CheckInDialog used in the ncig-merchandiser
		// POS app (front camera, 4:3 aspect, mirrored preview, 0.8 quality).
		console.info("[Selfie] capture_selfie invoked for", frm.doctype, frm.doc.name);

		if (!navigator.mediaDevices?.getUserMedia) {
			frappe.msgprint({
				message: __("Camera is not supported by your current browser"),
				title: __("Camera Error"),
				indicator: "red",
			});
			return;
		}

		let stream = null;
		let captured_data_url = null;

		const dialog = new frappe.ui.Dialog({
			title: __("Capture Selfie"),
			fields: [
				{
					fieldname: "selfie_html",
					fieldtype: "HTML",
					options: `
						<div class="selfie-wrap" style="text-align:center;">
							<div style="position:relative;background:#000;border-radius:8px;overflow:hidden;aspect-ratio:4/3;">
								<video class="selfie-video" autoplay playsinline muted
									style="width:100%;height:100%;object-fit:cover;transform:scaleX(-1);"></video>
								<img class="selfie-preview" alt="Selfie preview"
									style="display:none;width:100%;height:100%;object-fit:cover;" />
							</div>
							<canvas class="selfie-canvas" style="display:none;"></canvas>
							<div class="selfie-error text-danger small mt-2" style="display:none;"></div>
						</div>
					`,
				},
			],
			primary_action_label: __("Take Photo"),
			primary_action: () => takePhoto(),
			secondary_action_label: __("Cancel"),
			secondary_action: () => dialog.hide(),
		});

		const $wrap = $(dialog.body).find(".selfie-wrap");
		const $video = $wrap.find(".selfie-video");
		const $preview = $wrap.find(".selfie-preview");
		const $canvas = $wrap.find(".selfie-canvas");
		const $error = $wrap.find(".selfie-error");

		const startCamera = async () => {
			try {
				stream = await navigator.mediaDevices.getUserMedia({
					video: {
						facingMode: "user",
						width: { ideal: 640 },
						height: { ideal: 480 },
					},
				});
				$video[0].srcObject = stream;
				$error.hide();
				console.info("[Selfie] Camera started");
			} catch (err) {
				console.error("[Selfie] Camera error:", err);
				$error
					.text(__("Camera access denied. Please allow camera permission."))
					.show();
			}
		};

		const stopCamera = () => {
			if (stream) {
				stream.getTracks().forEach((t) => t.stop());
				stream = null;
				console.info("[Selfie] Camera stopped");
			}
		};

		const takePhoto = () => {
			const video = $video[0];
			const canvas = $canvas[0];
			if (!video || !video.videoWidth) {
				console.warn("[Selfie] Video not ready");
				return;
			}
			canvas.width = video.videoWidth;
			canvas.height = video.videoHeight;
			const ctx = canvas.getContext("2d");
			// Mirror the front-camera frame so the saved image matches preview.
			ctx.translate(canvas.width, 0);
			ctx.scale(-1, 1);
			ctx.drawImage(video, 0, 0);
			ctx.setTransform(1, 0, 0, 1, 0, 0);

			captured_data_url = canvas.toDataURL("image/jpeg", 0.8);
			$preview.attr("src", captured_data_url).show();
			$video.hide();
			stopCamera();

			dialog.set_primary_action(__("Use Photo"), () =>
				uploadAndAttach(captured_data_url),
			);
			dialog.set_secondary_action_label(__("Retake"));
			dialog.set_secondary_action(retake);
			console.info("[Selfie] Photo captured, awaiting confirmation");
		};

		const retake = async () => {
			captured_data_url = null;
			$preview.hide();
			$video.show();
			dialog.set_primary_action(__("Take Photo"), takePhoto);
			dialog.set_secondary_action_label(__("Cancel"));
			dialog.set_secondary_action(() => dialog.hide());
			await startCamera();
		};

		const uploadAndAttach = async (data_url) => {
			frappe.dom.freeze(__("Uploading selfie") + "...");
			try {
				const blob = await (await fetch(data_url)).blob();
				const filename = `selfie-${frm.doctype}-${frm.doc.name || "new"}-${Date.now()}.jpg`;
				const file = new File([blob], filename, { type: "image/jpeg" });

				const fd = new FormData();
				fd.append("file", file, filename);
				fd.append("is_private", "0");
				// Only pass doctype/docname/fieldname when we have a real, saved
				// docname — otherwise Frappe's upload_file throws "Attached To Name
				// must be a string or an integer". For unsaved records, upload the
				// file standalone and just write the returned file_url to selfie_image.
				if (frm.doc.name && !frm.doc.__islocal) {
					fd.append("doctype", frm.doctype);
					fd.append("docname", frm.doc.name);
					fd.append("fieldname", "selfie_image");
				}

				const res = await fetch("/api/method/upload_file", {
					method: "POST",
					headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
					body: fd,
				});
				const out = await res.json();
				if (!res.ok || !out?.message?.file_url) {
					throw new Error(out?.exception || __("Upload failed"));
				}
				await frm.set_value("selfie_image", out.message.file_url);
				frappe.show_alert({
					message: __("Selfie captured"),
					indicator: "green",
				});
				console.info("[Selfie] Uploaded:", out.message.file_url);
				dialog.hide();
			} catch (err) {
				console.error("[Selfie] Upload error:", err);
				frappe.msgprint({
					message: __("Failed to attach selfie: {0}", [err.message || err]),
					title: __("Upload Error"),
					indicator: "red",
				});
			} finally {
				frappe.dom.unfreeze();
			}
		};

		dialog.$wrapper.on("hidden.bs.modal", stopCamera);
		dialog.show();
		await startCamera();
	},

	get_doctype_fields_for_autocompletion: (doctype) => {
		const fields = frappe.get_meta(doctype).fields;
		const autocompletions = [];

		fields
			.filter((df) => !frappe.model.no_value_type.includes(df.fieldtype))
			.map((df) => {
				autocompletions.push({
					value: df.fieldname,
					score: 8,
					meta: __("{0} Field", [doctype]),
				});
			});

		return autocompletions;
	},

	add_shift_tools_button_to_list: (list_view, action = "Assign Shift") => {
		list_view.page.add_inner_button(
			__("Shift Assignment Tool"),
			() => {
				const doc = frappe.model.get_new_doc("Shift Assignment Tool");
				doc.action = action;
				doc.company = frappe.defaults.get_default("company");
				doc.status = "Active";
				frappe.set_route("Form", "Shift Assignment Tool", doc.name);
			},
			__("Shift Tools"),
		);

		list_view.page.add_inner_button(
			__("Roster"),
			() => {
				window.location.href = "/hr/roster";
			},
			__("Shift Tools"),
		);
	},

	add_shift_tools_button_to_form: (frm, fields) => {
		frm.add_custom_button(
			__("Shift Assignment Tool"),
			() => {
				const doc = frappe.model.get_new_doc("Shift Assignment Tool");
				Object.assign(doc, fields);
				doc.company = frappe.defaults.get_default("company");
				doc.status = "Active";
				frappe.set_route("Form", "Shift Assignment Tool", doc.name);
			},
			__("Shift Tools"),
		);
		frm.add_custom_button(
			__("Roster"),
			() => {
				window.location.href = "/hr/roster";
			},
			__("Shift Tools"),
		);
	},
});
