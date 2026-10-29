"""The text of a job description file, for the Manpower Request wizard (owner, 29 Oct 2026).

"when hiring manager attach the attachment of the JD it will auto reflect the job description
but still can be edit". The wizard uploads the file as it does any attachment, then asks
`read_job_description` for its text and puts it in the Draft job description box, which stays
editable. Reads PDF (pypdf, already a Frappe dependency), Word .docx (its XML, no library) and
plain text. A photo, a scanned PDF or an old .doc has no text to take: the answer is "" and the
person types it, exactly as before. Nothing is saved here.
"""

import io
import logging
import re
import zipfile
from xml.etree import ElementTree

import frappe
from frappe import _

logger = logging.getLogger(__name__)

#: Longer than any JD; keeps a 300-page PDF from landing in a text box.
MAX_CHARS = 20000

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def tidy(text: str) -> str:
	"""Unix line ends, no trailing spaces, at most one blank line in a row, capped."""
	lines = [line.rstrip() for line in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")]
	joined = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
	return joined[:MAX_CHARS]


def _pdf_text(content: bytes) -> str:
	from pypdf import PdfReader

	pages = [page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages]
	return "\n\n".join(p.strip() for p in pages if p and p.strip())


def _docx_text(content: bytes) -> str:
	with zipfile.ZipFile(io.BytesIO(content)) as archive:
		root = ElementTree.fromstring(archive.read("word/document.xml"))
	paragraphs = []
	for paragraph in root.iter(f"{_WORD_NS}p"):
		parts = []
		for node in paragraph.iter():
			if node.tag == f"{_WORD_NS}t":
				parts.append(node.text or "")
			elif node.tag == f"{_WORD_NS}tab":
				parts.append("\t")
			elif node.tag in (f"{_WORD_NS}br", f"{_WORD_NS}cr"):
				parts.append("\n")
		paragraphs.append("".join(parts))
	return "\n".join(paragraphs)


_READERS = {
	"pdf": _pdf_text,
	"docx": _docx_text,
	"txt": lambda content: content.decode("utf-8", errors="replace"),
}


def text_from_file(file_name: str, content: bytes) -> str:
	"""The file's text, tidied; "" when the kind has no text or the file cannot be read."""
	kind = file_name.rsplit(".", 1)[-1].lower() if "." in (file_name or "") else ""
	reader = _READERS.get(kind)
	if not reader:
		logger.info("[jd_text] %s: not a text kind (%s), nothing read", file_name, kind or "none")
		return ""
	try:
		text = tidy(reader(content or b""))
	except Exception as error:
		# a damaged or locked file is only attached; the person types the description
		logger.warning("[jd_text] %s: could not read (%s)", file_name, error)
		return ""
	logger.info("[jd_text] %s: %d character(s) read", file_name, len(text))
	return text


@frappe.whitelist(methods=["POST"])
def read_job_description(file_url: str) -> dict:
	"""The text of the caller's own just-uploaded file (not yet filed under any request)."""
	row = frappe.db.get_value(
		"File",
		{"file_url": file_url, "owner": frappe.session.user},
		["name", "file_name", "owner", "attached_to_name"],
		as_dict=True,
	)
	if not row or row.owner != frappe.session.user or row.attached_to_name:
		logger.warning("[jd_text] %s refused %s", frappe.session.user, file_url)
		frappe.throw(_("You can only read a file you have just added."), frappe.PermissionError)
	content = frappe.get_doc("File", row.name).get_content()
	if isinstance(content, str):
		content = content.encode("utf-8")
	return {"text": text_from_file(row.file_name, content), "file_name": row.file_name}
