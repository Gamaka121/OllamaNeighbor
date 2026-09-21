import subprocess
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def open_notepad(text=""):
    subprocess.Popen(["notepad.exe"])

    time.sleep(1)

    if text:
        try:
            window = Desktop(
                backend="uia"
            ).window(
                title_re=r".*(Notepad|Блокнот).*"
            )

            window.set_focus()

            send_keys(
                text,
                with_spaces=True
            )

        except Exception as e:
            return f"Блокнот открыт, но текст не удалось ввести: {e}"

    return "Блокнот открыт."


def open_calculator():
    subprocess.Popen(["calc.exe"])

    return "Калькулятор открыт."


def press_key(key):
    try:
        send_keys(key)
        return f"Нажата клавиша: {key}"
    except Exception as e:
        return f"Ошибка клавиатуры: {e}"


def type_text(text):
    try:
        send_keys(
            text,
            with_spaces=True
        )

        return "Текст напечатан."

    except Exception as e:
        return f"Ошибка ввода текста: {e}"
