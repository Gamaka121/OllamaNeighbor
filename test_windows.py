"""Ручная проверка Windows-интеграции.

Это не unit-тест: запуск требует интерактивного рабочего стола и открывает
Блокнот. Поэтому модуль не выполняет побочных действий при импорте.
"""

from tools.windows import open_notepad


def manual_smoke_test():
    result = open_notepad("Привет! Это текст, который отправил локальный AI.")
    print(result)


if __name__ == "__main__":
    manual_smoke_test()
