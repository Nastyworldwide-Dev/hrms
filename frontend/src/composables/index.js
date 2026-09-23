import { createResource, toast } from "frappe-ui"
import { firstMessage } from "@/utils/loudRequest"

function getFileReader() {
	const fileReader = new FileReader()
	const zoneOriginalInstance = fileReader["__zone_symbol__originalInstance"]
	return zoneOriginalInstance || fileReader
}

export class FileAttachment {
	constructor(fileObj) {
		this.fileObj = fileObj
		this.fileName = fileObj.name
	}

	async upload(documentType, documentName, fieldName) {
		// Not `async (resolve, reject) =>` — nothing inside ever awaits, and an
		// async executor swallows a synchronous throw as an unhandled rejection
		// on a promise nothing holds, instead of calling reject(): a bad file
		// object would have hung this upload forever rather than failing it.
		return new Promise((resolve, reject) => {
			const reader = getFileReader()
			const uploader = createResource({
				url: "hrms.api.upload_base64_file",
				onSuccess: (fileDoc) => resolve(fileDoc),
				onError: (error) => {
					toast({
						title: "Error",
						text: `File upload failed for ${this.fileName}. ${firstMessage(error, "")}`,
						icon: "alert-circle",
						position: "bottom-center",
						iconClasses: "text-red-500",
					})
					reject(error)
				},
			})

			reader.onload = () => {
				console.log("Loaded successfully ✅")
				this.fileContents = reader.result.toString().split(",")[1]

				uploader.submit({
					content: this.fileContents,
					dt: documentType,
					dn: documentName,
					filename: this.fileName,
					fieldname: fieldName,
				})
			}
			reader.readAsDataURL(this.fileObj)
		})
	}

	delete() {
		return createResource({
			url: "hrms.api.delete_attachment",
			onSuccess: () => {
				console.log("Deleted successfully ✅")
			},
			onError: (error) => {
				toast({
					title: "Error",
					text: `File deletion failed. ${firstMessage(error, "")}`,
					icon: "alert-circle",
					position: "bottom-center",
					iconClasses: "text-red-500",
				})
			},
		}).submit({
			filename: this.fileName,
		})
	}
}
