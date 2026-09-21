from pathlib import Path

from openpyxl import Workbook
from docx import Document


DOCUMENTS_DIR = (
    Path.home() /
    "Documents" /
    "OllamaNeighbor"
)

DOCUMENTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def create_excel(filename, data):
    filename = Path(filename).name

    if not filename.lower().endswith(".xlsx"):
        filename += ".xlsx"

    path = DOCUMENTS_DIR / filename

    workbook = Workbook()
    sheet = workbook.active

    for row in data:
        sheet.append(row)

    workbook.save(path)

    return f"Excel-файл создан: {path}"


def create_word(filename, text):
    filename = Path(filename).name

    if not filename.lower().endswith(".docx"):
        filename += ".docx"

    path = DOCUMENTS_DIR / filename

    document = Document()

    for paragraph in text.split("\n"):
        document.add_paragraph(paragraph)

    document.save(path)

    return f"Word-документ создан: {path}"
