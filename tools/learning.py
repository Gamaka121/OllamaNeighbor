"""Безопасное обучение Ollama Neighbor на подтверждённом опыте.

Модуль не меняет веса модели и не редактирует код. Он хранит только
проверенные уроки из успешных задач, чтобы использовать их в следующих
похожих запросах.
"""

from __future__ import annotations

import json
import re
import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


LEARNING_VERSION = 1
MAX_TASKS = 100
MAX_LESSONS = 80
MAX_LESSON_CHARS = 500
_LOCK = threading.RLock()

# Такие сведения могут быть полезны в текущем диалоге, но не являются уроком.
RUNTIME_WORDS = (
    "текущее время", "сейчас ", "cpu", "озу", "ram", "погод",
    "новост", "курс валют", "цен", "процесс", "ip-адрес",
)

RUNTIME_TOOLS = {
    "get_current_datetime", "get_pc_info", "get_processes",
    "web_search", "read_webpage", "play_yt_music",
    "get_exchange_rate", "get_weather_forecast",
}


def _contains_runtime_data(text: str) -> bool:
    lower = " ".join(str(text).lower().split())
    return any(word in lower for word in RUNTIME_WORDS)


def _empty_learning() -> dict[str, Any]:
    return {
        "version": LEARNING_VERSION,
        "tasks": [],
        "candidates": [],
        "lessons": [],
    }


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _normalize(data: Any) -> dict[str, Any]:
    result = _empty_learning()

    if not isinstance(data, dict):
        return result

    for name, limit in (("tasks", MAX_TASKS), ("candidates", MAX_LESSONS), ("lessons", MAX_LESSONS)):
        value = data.get(name)
        if isinstance(value, list):
            clean = []
            for item in value:
                if not isinstance(item, dict):
                    continue

                text = f"{item.get('request', '')} {item.get('answer', '')} {item.get('text', '')}"
                if _contains_runtime_data(text):
                    continue

                if set(item.get("tools", [])) & RUNTIME_TOOLS:
                    continue

                clean.append(deepcopy(item))

            result[name] = clean[-limit:]

    return result


def load_learning(path: Path) -> dict[str, Any]:
    with _LOCK:
        try:
            data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        except Exception:
            data = {}

        learning = _normalize(data)
        save_learning(path, learning)
        return learning


def save_learning(path: Path, learning: dict[str, Any]) -> bool:
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")

        try:
            temporary.write_text(
                json.dumps(_normalize(learning), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(path)
            return True
        except Exception:
            try:
                temporary.unlink(missing_ok=True)
            except Exception:
                pass
            return False


def record_task(learning: dict[str, Any], request: str, answer: str, tool_names: list[str] | None = None) -> None:
    """Сохраняет краткую запись задачи; это ещё не урок."""
    request = str(request).strip()
    answer = str(answer).strip()
    if not request or not answer:
        return

    tool_names = [str(name) for name in (tool_names or [])]

    # Актуальные данные не могут стать материалом для обучения.
    if (
        _contains_runtime_data(request)
        or _contains_runtime_data(answer)
        or set(tool_names) & RUNTIME_TOOLS
    ):
        return

    learning.setdefault("tasks", []).append({
        "id": uuid4().hex,
        "created_at": _now(),
        "request": request[:4000],
        "answer": answer[:4000],
        "tools": tool_names[:20],
        "confirmed": False,
    })
    learning["tasks"] = learning["tasks"][-MAX_TASKS:]


def latest_unconfirmed_task(learning: dict[str, Any]) -> dict[str, Any] | None:
    for task in reversed(learning.get("tasks", [])):
        if not task.get("confirmed"):
            return task
    return None


def is_safe_lesson(text: str) -> bool:
    clean = " ".join(str(text).split())
    return bool(clean) and len(clean) <= MAX_LESSON_CHARS and not _contains_runtime_data(clean)


def promote_lesson(learning: dict[str, Any], task_id: str, lesson: str, category: str = "project") -> bool:
    """Подтверждает урок и заменяет семантически одинаковый старый урок."""
    lesson = " ".join(str(lesson).split())
    if not is_safe_lesson(lesson):
        return False

    for task in learning.get("tasks", []):
        if task.get("id") == task_id:
            task["confirmed"] = True
            break
    else:
        return False

    key = re.sub(r"[^a-zа-я0-9]+", " ", lesson.lower()).strip()[:80]
    entry = {
        "id": uuid4().hex,
        "category": re.sub(r"[^a-z_]+", "", category.lower()) or "project",
        "text": lesson,
        "key": key,
        "created_at": _now(),
        "task_id": task_id,
    }

    lessons = learning.setdefault("lessons", [])
    for index, old in enumerate(lessons):
        if old.get("key") == key:
            lessons[index] = entry
            break
    else:
        lessons.append(entry)

    learning["lessons"] = lessons[-MAX_LESSONS:]
    return True


def build_learning_context(learning: dict[str, Any], user_text: str, limit: int = 6) -> str:
    """Возвращает только уроки, похожие на текущую задачу."""
    words = set(re.findall(r"[a-zа-я0-9_]{3,}", str(user_text).lower()))
    ranked = []

    for lesson in learning.get("lessons", []):
        text = str(lesson.get("text", ""))
        score = len(words.intersection(re.findall(r"[a-zа-я0-9_]{3,}", text.lower())))
        if score:
            ranked.append((score, text))

    if not ranked:
        return ""

    lines = [f"- {text}" for _, text in sorted(ranked, reverse=True)[:limit]]
    return (
        "ПРОВЕРЕННЫЕ УРОКИ ПРОЕКТА\n"
        + "\n".join(lines)
        + "\nИспользуй их как технические рекомендации, но проверяй их применимость."
    )
