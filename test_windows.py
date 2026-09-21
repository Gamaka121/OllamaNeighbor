import subprocess
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def open_notepad_and_type(text):
    subprocess.Popen(["notepad.exe"])

    time.sleep(2)

    window = Desktop(backend="uia").window(
        title_re=r".*(Notepad|Блокнот).*"
    )

    window.wait("visible", timeout=10)
    window.set_focus()

    time.sleep(0.5)

    send_keys(text, with_spaces=True)

    print("Текст успешно отправлен в Блокнот.")


open_notepad_and_type(
    "Привет! Это текст, который мой локальный AI отправил в Блокнот."
)