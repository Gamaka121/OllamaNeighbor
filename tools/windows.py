"""Явные GUI-действия Windows; не используются для работы с файлами."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pywinauto.keyboard import send_keys


def _ok(message, **data):
    return {"success": True, "message": message, "data": data}


def _error(message, **data):
    return {"success": False, "error": message, "data": data}


def open_notepad(text=""):
    """Открывает новый экземпляр Notepad и, при наличии текста, безопасно передает его."""
    try:
        if text:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
                f.write(str(text))
                temp_path = f.name
            process = subprocess.Popen(["notepad.exe", temp_path])
            return _ok(
                "Открыт новый экземпляр Блокнота с переданным текстом.",
                pid=process.pid,
                path=temp_path,
                text_sent=True,
            )
        else:
            process = subprocess.Popen(["notepad.exe"])
            return _ok(
                "Открыт Блокнот.",
                pid=process.pid,
                text_sent=False,
            )
    except OSError as error:
        return _error(f"Не удалось запустить Блокнот: {error}")


def open_calculator():
    try:
        process = subprocess.Popen(["calc.exe"])
    except OSError as error:
        return _error(f"Не удалось запустить Калькулятор: {error}")
    return _ok("Команда запуска Калькулятора передана Windows.", pid=process.pid)


def press_key(key):
    key = str(key or "").strip()
    if not key:
        return _error("Не указана клавиша.")
    try:
        send_keys(key)
    except Exception as error:
        return _error(f"Не удалось отправить клавишу: {error}", key=key)
    return _ok("Команда нажатия клавиши отправлена активному окну.", key=key)


def type_text(text):
    text = str(text or "")
    if not text:
        return _error("Не указан текст для ввода.")
    try:
        send_keys(text, with_spaces=True)
    except Exception as error:
        return _error(f"Не удалось отправить текст: {error}")
    return _ok("Команда ввода текста отправлена активному окну.", characters=len(text))


def type_text_and_press_key(text, key):
    """Атомарная по порядку последовательность: ввод, затем клавиша."""
    typed = type_text(text)
    if not typed["success"]:
        return typed
    pressed = press_key(key)
    if not pressed["success"]:
        return _error("Текст отправлен, но клавиша не была отправлена.", typed=True, key=key)
    return _ok("Текст и клавиша последовательно отправлены активному окну.", key=str(key), characters=len(str(text)))
