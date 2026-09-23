"""Filesystem operations for Ollama Neighbor."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
NOTES_DIR = Path.home() / "Documents" / "OllamaNeighbor"
DESKTOP_DIR = Path.home() / "Desktop"
DOCUMENTS_DIR = Path.home() / "Documents"
DOWNLOADS_DIR = Path.home() / "Downloads"

# Neighbor может читать всю файловую систему Windows. Изменение и удаление
# тоже технически разрешены, но вызываются только после явного UI-подтверждения
# в main.py. Ограничение .. и UNC-путей сохраняется.
WINDOWS_ROOT = Path("C:\\")
READ_ROOTS = (WINDOWS_ROOT,)
WRITE_ROOTS = (WINDOWS_ROOT,)
MAX_TEXT_FILE_BYTES = 2 * 1024 * 1024
MAX_FIND_RESULTS = 100


def _ok(message, **data):
    return {"success": True, "message": message, "data": data}


def _error(message, **data):
    return {"success": False, "error": message, "data": data}


def _notes_dir() -> Path:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return NOTES_DIR.resolve()


def _extract_special_folder(value: str) -> Path | None:
    raw = str(value or "").strip().lower().replace("/", "\\")
    if raw in {"desktop", "рабочий стол", "на рабочем столе", "рабочем столе"}:
        return DESKTOP_DIR
    if raw in {"downloads", "загрузки", "в загрузках"}:
        return DOWNLOADS_DIR
    if raw in {"documents", "документы", "в документах"}:
        return DOCUMENTS_DIR
    if raw in {"home", "домашняя папка", "домашний каталог", "домой"}:
        return Path.home()
    if raw in {"project", "проект", "папка проекта"}:
        return PROJECT_DIR
    return None


def _is_within(path: Path, root: Path) -> bool:
    try:
        resolved_path = path.resolve(strict=False)
        resolved_root = root.resolve(strict=False)
        resolved_path.relative_to(resolved_root)
        return True
    except (ValueError, OSError):
        return False


def _normalize_path(value, default_root=None, allowed_roots=None):
    if default_root is None:
        default_root = _notes_dir()
    if allowed_roots is None:
        allowed_roots = globals().get("READ_ROOTS", (WINDOWS_ROOT,))

    raw = str(value or "").strip().strip("'\"").replace("/", "\\")
    if not raw:
        return None, "Не указан путь."

    if len(raw) == 2 and raw[0].isalpha() and raw[1] == ":":
        raw = raw + "\\"

    if len(raw) >= 3 and raw[0].isalpha() and raw[1] == "\\" and raw[2] == ":":
        return None, "Некорректная запись диска. Используйте формат C:\\папка."

    if raw.startswith("\\\\"):
        return None, "UNC-пути не поддерживаются."

    special = _extract_special_folder(raw)
    candidate = special if special is not None else Path(raw)

    if ".." in candidate.parts:
        return None, "Пути с '..' не разрешены."

    path = candidate if candidate.is_absolute() else default_root / candidate
    try:
        resolved = path.resolve(strict=False)
    except OSError as error:
        return None, f"Некорректный путь: {error}"

    allowed_list = list(allowed_roots)
    if not any(_is_within(resolved, root) for root in allowed_list):
        allowed = ", ".join(str(root.resolve(strict=False)) for root in allowed_list)
        return None, f"Путь вне разрешённых областей. Доступны: {allowed}"

    return resolved, None


def _read_path(path=None):
    if path is None or not str(path).strip():
        return _notes_dir(), None
    return _normalize_path(path, _notes_dir(), READ_ROOTS)


def _write_path(filename):
    if filename is None or not str(filename).strip():
        return None, "Не указан путь или имя файла."
    return _normalize_path(filename, _notes_dir(), WRITE_ROOTS)


def get_files_directory():
    return _ok("Папка данных Neighbor определена.", path=str(_notes_dir()))


def get_path_info(path):
    resolved, error = _read_path(path)
    if error:
        return _error(error, path=str(path or ""))
    if not resolved.exists():
        return _error(f"Путь не существует: {resolved}", path=str(resolved))
    return _ok("Информация о пути получена.", path=str(resolved), exists=True,
               kind="directory" if resolved.is_dir() else "file",
               size=resolved.stat().st_size if resolved.is_file() else None)


def list_files(path=None):
    if path is not None and str(path).strip():
        resolved, error = _read_path(path)
        if error:
            return _error(error, path=str(path))
        if not resolved.exists():
            return _error(f"Директория не существует: {resolved}", path=str(resolved))
        if not resolved.is_dir():
            return _error(f"Указанный путь не является папкой: {resolved}", path=str(resolved))
    else:
        resolved = _notes_dir()

    try:
        entries = sorted(
            ({"name": item.name, "type": "directory" if item.is_dir() else "file"}
             for item in resolved.iterdir()),
            key=lambda item: (item["type"] != "directory", item["name"].lower()),
        )
    except OSError as error:
        return _error(f"Не удалось прочитать папку: {error}", path=str(resolved))
    return _ok("Содержимое папки получено.", path=str(resolved), entries=entries)


def find_file(path, name):
    resolved, error = _read_path(path)
    name = Path(str(name or "")).name.strip()
    if error:
        return _error(error, path=str(path or ""))
    if not name or name in {".", ".."}:
        return _error("Укажите имя файла или папки.")
    if not resolved.is_dir():
        return _error(f"Папка для поиска не найдена: {resolved}", path=str(resolved))
    matches = []
    try:
        for root, directories, files in os.walk(resolved, followlinks=False):
            directories[:] = [d for d in directories if not Path(root, d).is_symlink()]
            for item in directories + files:
                if item.lower() == name.lower():
                    found = Path(root, item).resolve()
                    if _is_within(found, resolved):
                        matches.append(str(found))
                if len(matches) >= MAX_FIND_RESULTS:
                    break
            if len(matches) >= MAX_FIND_RESULTS:
                break
    except OSError as error:
        return _error(f"Не удалось выполнить поиск: {error}", path=str(resolved))
    return _ok("Поиск завершён.", path=str(resolved), name=name, matches=matches)


def create_text_file(filename, content):
    path, error = _write_path(filename)
    if error:
        return _error(error, path=str(filename or ""))
    if path.suffix.lower() != ".txt":
        path = path.with_suffix(".txt")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
    except OSError as error:
        return _error(f"Не удалось создать файл: {error}", path=str(path))
    return _ok("Текстовый файл создан.", path=str(path), operation="create", type="file")


def read_text_file(filename=None, path=None):
    target, error = _read_path(path if path is not None else filename)
    if error:
        return _error(error, path=str(path if path is not None else filename or ""))
    if not target.is_file():
        return _error(f"Файл не найден: {target}", path=str(target))
    try:
        if target.stat().st_size > MAX_TEXT_FILE_BYTES:
            return _error("Файл слишком большой для чтения (лимит 2 МБ).", path=str(target))
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return _error("Файл не является текстом UTF-8.", path=str(target))
    except OSError as error:
        return _error(f"Не удалось прочитать файл: {error}", path=str(target))
    return _ok("Текстовый файл прочитан.", path=str(target), content=content, type="file")


def write_text_file(filename, content):
    path, error = _write_path(filename)
    if error:
        return _error(error, path=str(filename or ""))
    if path.suffix.lower() != ".txt":
        path = path.with_suffix(".txt")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")
    except OSError as error:
        return _error(f"Не удалось сохранить файл: {error}", path=str(path))
    return _ok("Текстовый файл сохранён.", path=str(path), operation="write", type="file")


def delete_file(filename):
    path, error = _write_path(filename)
    if error:
        return _error(error, path=str(filename or ""))
    if not path.is_file():
        return _error(f"Файл не найден: {path}", path=str(path))
    try:
        path.unlink()
    except OSError as error:
        return _error(f"Не удалось удалить файл: {error}", path=str(path))
    return _ok("Файл удалён.", path=str(path), operation="delete", exists=False, type="file")


def create_folder(name):
    path, error = _write_path(name)
    if error:
        return _error(error, path=str(name or ""))
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        return _error(f"Не удалось создать папку: {error}", path=str(path))
    return _ok("Папка создана.", path=str(path), operation="create_directory", type="directory")


def open_folder(path=None):
    target_path = path if path is not None and str(path).strip() else _notes_dir()
    resolved, error = _read_path(target_path)
    if error:
        return _error(error, path=str(target_path))
    if not resolved.exists():
        return _error(f"Папка не существует: {resolved}", path=str(resolved))
    if not resolved.is_dir():
        return _error(f"Указанный путь является файлом, а не папкой. Используйте open_file: {resolved}", path=str(resolved), type="file")
    try:
        os.startfile(resolved)
    except OSError as error:
        return _error(f"Windows не удалось открыть папку: {error}", path=str(resolved))
    return _ok("Папка открыта.", path=str(resolved), operation="open_directory", type="directory")


def open_file(filename=None, path=None):
    raw_path = path if path is not None else filename
    if not raw_path or not str(raw_path).strip():
        return _error("Не указан путь к файлу.")
    resolved, error = _read_path(raw_path)
    if error:
        return _error(error, path=str(raw_path))
    if not resolved.exists():
        return _error(f"Файл не существует: {resolved}", path=str(resolved))
    if resolved.is_dir():
        return _error(f"Указанный путь является папкой, а не файлом. Используйте open_folder: {resolved}", path=str(resolved), type="directory")
    try:
        os.startfile(resolved)
    except OSError as error:
        return _error(f"Windows не удалось открыть путь: {error}", path=str(resolved))
    return _ok("Файл открыт.", path=str(resolved), operation="open_file", type="file")
