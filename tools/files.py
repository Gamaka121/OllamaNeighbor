from pathlib import Path
import shutil


NOTES_DIR = Path.home() / "Documents" / "OllamaNeighbor"
NOTES_DIR.mkdir(parents=True, exist_ok=True)


def safe_path(filename):
    filename = Path(filename).name
    return NOTES_DIR / filename


def create_text_file(filename, content):
    path = safe_path(filename)

    if path.suffix.lower() != ".txt":
        path = path.with_suffix(".txt")

    path.write_text(content, encoding="utf-8")

    return f"Создан файл: {path}"


def read_text_file(filename):
    path = safe_path(filename)

    if not path.exists():
        return f"Файл не найден: {path}"

    return path.read_text(encoding="utf-8")


def write_text_file(filename, content):
    path = safe_path(filename)

    path.write_text(content, encoding="utf-8")

    return f"Файл сохранён: {path}"


def list_files():
    files = sorted(
        p.name
        for p in NOTES_DIR.iterdir()
        if p.is_file()
    )

    if not files:
        return "Папка OllamaNeighbor пока пустая."

    return "\n".join(
        f"- {filename}"
        for filename in files
    )


def delete_file(filename):
    path = safe_path(filename)

    if not path.exists():
        return f"Файл не найден: {path}"

    path.unlink()

    return f"Удалён файл: {path}"


def create_folder(name):
    folder_name = Path(name).name
    path = NOTES_DIR / folder_name

    path.mkdir(
        parents=True,
        exist_ok=True
    )

    return f"Создана папка: {path}"


def open_file(filename):
    path = safe_path(filename)

    if not path.exists():
        return f"Файл не найден: {path}"

    import os
    os.startfile(path)

    return f"Открыт файл: {path}"
