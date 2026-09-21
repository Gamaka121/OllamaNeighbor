"""
tools/memory.py

Структурированная долговременная память Ollama Neighbor.

ВАЖНО:
- memory.json НЕ является полной историей всех сообщений.
- runtime/tool results не сохраняются как долговременные факты.
- conversation содержит только ограниченный недавний контекст.
- profile/facts/preferences/projects/decisions предназначены
  для долговременной информации.
"""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path
from typing import Any


MEMORY_VERSION = 2

MAX_CONVERSATION_MESSAGES = 80
MAX_FACTS = 100
MAX_PREFERENCES = 100
MAX_PROJECTS = 50
MAX_DECISIONS = 100

_LOCK = threading.RLock()


def _empty_memory() -> dict[str, Any]:
    return {
        "version": MEMORY_VERSION,
        "profile": {},
        "facts": [],
        "preferences": [],
        "projects": [],
        "decisions": [],
        "conversation": [],
    }


def _normalize_string(value: Any) -> str:
    return str(value).strip()


def _normalize_memory(data: Any) -> dict[str, Any]:
    """
    Приводит данные к строго заданной структуре v2.

    Старый список сообщений намеренно НЕ мигрируется:
    по требованиям проекта старой memory.json не существует.
    """

    result = _empty_memory()

    if not isinstance(data, dict):
        return result

    result["version"] = MEMORY_VERSION

    profile = data.get("profile")
    if isinstance(profile, dict):
        result["profile"] = {
            str(key): value
            for key, value in profile.items()
            if isinstance(key, str)
        }

    for section, limit in (
        ("facts", MAX_FACTS),
        ("preferences", MAX_PREFERENCES),
        ("projects", MAX_PROJECTS),
        ("decisions", MAX_DECISIONS),
    ):
        value = data.get(section)

        if not isinstance(value, list):
            continue

        clean = []

        for item in value:
            if isinstance(item, dict):
                clean.append(deepcopy(item))
            elif isinstance(item, str) and item.strip():
                clean.append(item.strip())

        result[section] = clean[-limit:]

    conversation = data.get("conversation")

    if isinstance(conversation, list):
        result["conversation"] = _normalize_conversation(
            conversation
        )

    return result


def _normalize_conversation(
    messages: list[Any],
) -> list[dict[str, Any]]:
    """
    Сохраняет только корректные user/assistant сообщения.

    Tool results намеренно не являются долговременной памятью.

    Assistant-сообщения с tool_calls сохраняются только тогда,
    когда их можно использовать как часть корректного текущего
    conversational context.
    """

    clean: list[dict[str, Any]] = []

    for item in messages:
        if not isinstance(item, dict):
            continue

        role = item.get("role")

        if role not in {"user", "assistant"}:
            continue

        if "content" not in item:
            continue

        message: dict[str, Any] = {
            "role": role,
            "content": str(item.get("content") or ""),
        }

        timestamp = item.get("timestamp")

        if timestamp:
            message["timestamp"] = str(timestamp)

        # Не сохраняем tool_calls в долговременной conversation.
        #
        # Причина:
        # assistant(tool_calls) требует соответствующие tool messages.
        # Tool messages намеренно не являются долговременной памятью.
        #
        # Поэтому assistant-сообщение с tool_calls превращается
        # в обычный conversational message только если у него есть
        # видимый текст.
        #
        # Если content пустой — такое техническое сообщение вообще
        # не нужно переносить в следующий запуск.

        content = message["content"]

        if role == "assistant" and not content.strip():
            continue

        clean.append(message)

    return clean[-MAX_CONVERSATION_MESSAGES:]


def load_memory(memory_file: Path) -> dict[str, Any]:
    """
    Загружает memory.json.

    Если файла нет или он повреждён — создаётся чистая структура v2.
    """

    with _LOCK:
        if not memory_file.exists():
            memory = _empty_memory()
            save_memory(memory_file, memory)
            return memory

        try:
            data = json.loads(
                memory_file.read_text(encoding="utf-8")
            )
        except Exception:
            memory = _empty_memory()
            save_memory(memory_file, memory)
            return memory

        memory = _normalize_memory(data)

        # Если структура была неполной — сразу приводим файл
        # к нормальной версии v2.
        if data != memory:
            save_memory(memory_file, memory)

        return memory


def save_memory(
    memory_file: Path,
    memory: dict[str, Any],
) -> bool:
    """
    Атомарно сохраняет memory.json.
    """

    with _LOCK:
        clean = _normalize_memory(memory)

        temp_file = memory_file.with_suffix(".tmp")

        try:
            temp_file.write_text(
                json.dumps(
                    clean,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temp_file.replace(memory_file)
            return True

        except Exception:
            try:
                temp_file.unlink(missing_ok=True)
            except Exception:
                pass

            return False


def get_empty_memory() -> dict[str, Any]:
    return _empty_memory()


def get_profile(
    memory: dict[str, Any],
) -> dict[str, Any]:
    profile = memory.get("profile")

    if not isinstance(profile, dict):
        profile = {}
        memory["profile"] = profile

    return profile


def update_profile(
    memory_file: Path,
    memory: dict[str, Any],
    key: str,
    value: Any,
) -> bool:
    key = _normalize_string(key)

    if not key:
        return False

    with _LOCK:
        profile = get_profile(memory)
        profile[key] = deepcopy(value)
        return save_memory(memory_file, memory)


def _entry_key(item: Any) -> str | None:
    if isinstance(item, dict):
        key = item.get("key")

        if key is not None:
            return _normalize_string(key)

        key = item.get("name")

        if key is not None:
            return _normalize_string(key)

        key = item.get("title")

        if key is not None:
            return _normalize_string(key)

    return None


def _upsert_list_entry(
    memory_file: Path,
    memory: dict[str, Any],
    section: str,
    value: Any,
    key: str | None = None,
    limit: int = 100,
) -> bool:
    with _LOCK:
        items = memory.setdefault(section, [])

        if not isinstance(items, list):
            items = []
            memory[section] = items

        normalized_key = (
            _normalize_string(key)
            if key is not None
            else None
        )

        # Ключ делает запись заменяемой. Храним его вместе со
        # значением, иначе строковая запись не сможет быть найдена
        # при следующем обновлении.
        stored_value = deepcopy(value)

        if normalized_key and not isinstance(stored_value, dict):
            stored_value = {
                "key": normalized_key,
                "value": stored_value,
            }

        replaced = False

        if normalized_key:
            for index, item in enumerate(items):
                if _entry_key(item) == normalized_key:
                    items[index] = stored_value
                    replaced = True
                    break

        if not replaced:
            items.append(stored_value)

        memory[section] = items[-limit:]

        return save_memory(memory_file, memory)


def add_fact(
    memory_file: Path,
    memory: dict[str, Any],
    value: str,
    key: str | None = None,
) -> bool:
    return _upsert_list_entry(
        memory_file,
        memory,
        "facts",
        value.strip(),
        key,
        MAX_FACTS,
    )


def add_preference(
    memory_file: Path,
    memory: dict[str, Any],
    value: str,
    key: str | None = None,
) -> bool:
    return _upsert_list_entry(
        memory_file,
        memory,
        "preferences",
        value.strip(),
        key,
        MAX_PREFERENCES,
    )


def add_project(
    memory_file: Path,
    memory: dict[str, Any],
    value: str,
    key: str | None = None,
) -> bool:
    return _upsert_list_entry(
        memory_file,
        memory,
        "projects",
        value.strip(),
        key,
        MAX_PROJECTS,
    )


def add_decision(
    memory_file: Path,
    memory: dict[str, Any],
    value: str,
    key: str | None = None,
) -> bool:
    return _upsert_list_entry(
        memory_file,
        memory,
        "decisions",
        value.strip(),
        key,
        MAX_DECISIONS,
    )


def add_conversation_message(
    memory: dict[str, Any],
    role: str,
    content: str,
    timestamp: str | None = None,
) -> None:
    """
    Добавляет только обычное user/assistant сообщение.

    Tool results сюда НЕ добавляются.
    """

    if role not in {"user", "assistant"}:
        return

    content = str(content or "")

    if not content.strip():
        return

    message: dict[str, Any] = {
        "role": role,
        "content": content,
    }

    if timestamp:
        message["timestamp"] = timestamp

    conversation = memory.setdefault(
        "conversation",
        [],
    )

    if not isinstance(conversation, list):
        conversation = []
        memory["conversation"] = conversation

    conversation.append(message)

    memory["conversation"] = _normalize_conversation(
        conversation
    )


def get_recent_conversation(
    memory: dict[str, Any],
    limit: int = MAX_CONVERSATION_MESSAGES,
) -> list[dict[str, Any]]:
    conversation = memory.get("conversation")

    if not isinstance(conversation, list):
        return []

    return deepcopy(
        _normalize_conversation(conversation)[-limit:]
    )


def clear_conversation(
    memory_file: Path,
    memory: dict[str, Any],
) -> bool:
    """
    Очищает ТОЛЬКО разговор.

    profile/facts/preferences/projects/decisions остаются.
    """

    with _LOCK:
        memory["conversation"] = []
        return save_memory(memory_file, memory)


def clear_all_memory(
    memory_file: Path,
) -> dict[str, Any]:
    """
    Полностью сбрасывает долговременную память.
    """

    memory = _empty_memory()
    save_memory(memory_file, memory)
    return memory


def build_memory_context(
    memory: dict[str, Any],
) -> str:
    """
    Формирует компактный контекст для system/user prompt.

    Runtime information сюда не попадает.
    """

    parts: list[str] = []

    profile = memory.get("profile")

    if isinstance(profile, dict) and profile:
        lines = []

        for key, value in profile.items():
            lines.append(f"- {key}: {value}")

        parts.append(
            "PROFILE:\n" + "\n".join(lines)
        )

    for section, title in (
        ("facts", "FACTS"),
        ("preferences", "PREFERENCES"),
        ("projects", "PROJECTS"),
        ("decisions", "DECISIONS"),
    ):
        items = memory.get(section)

        if not isinstance(items, list) or not items:
            continue

        lines = []

        for item in items:
            if isinstance(item, dict):
                key = item.get("key")

                if key:
                    value = item.get("value", "")
                    lines.append(
                        f"- {key}: {value}"
                    )
                else:
                    lines.append(
                        "- " + json.dumps(
                            item,
                            ensure_ascii=False,
                        )
                    )
            else:
                lines.append(f"- {item}")

        parts.append(
            f"{title}:\n" + "\n".join(lines)
        )

    if not parts:
        return (
            "Долговременная память пользователя "
            "пока пуста."
        )

    return (
        "ДОЛГОВРЕМЕННАЯ ПАМЯТЬ\n"
        "=======================\n"
        + "\n\n".join(parts)
        + "\n\n"
        "ВАЖНО: эта память НЕ является текущим состоянием "
        "компьютера и НЕ содержит актуальные время, дату, "
        "погоду, новости, цены, CPU, RAM или результаты "
        "инструментов."
    )
