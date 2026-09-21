"""
tools/system.py — информация о локальном компьютере.
"""

from datetime import datetime

import platform
import psutil


def get_pc_info():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("C:\\")

    return (
        f"Система: {platform.system()} {platform.release()}\n"
        f"Процессор: {platform.processor()}\n"
        f"CPU: {cpu}%\n"
        f"ОЗУ: {memory.percent}% "
        f"({memory.used // (1024**3)} / "
        f"{memory.total // (1024**3)} ГБ)\n"
        f"Диск C: {disk.percent}% "
        f"({disk.used // (1024**3)} / "
        f"{disk.total // (1024**3)} ГБ)"
    )


def get_processes():
    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "memory_percent"]
    ):
        try:
            info = process.info

            processes.append(
                (
                    info["memory_percent"] or 0,
                    info["pid"],
                    info["name"],
                )
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    processes.sort(reverse=True)

    result = "Процессы:\n"

    for memory, pid, name in processes[:15]:
        result += (
            f"{name} | PID {pid} | "
            f"RAM {memory:.1f}%\n"
        )

    return result


def get_current_datetime():
    """
    Возвращает текущие дату, время и часовой пояс
    непосредственно с компьютера пользователя.

    Каждый вызов получает новое значение.
    Интернет и memory.json здесь не используются.
    """

    now = datetime.now().astimezone()

    timezone_name = now.tzname() or "локальный"

    return (
        "ТЕКУЩИЕ ДАТА И ВРЕМЯ КОМПЬЮТЕРА\n"
        f"Дата: {now.strftime('%d.%m.%Y')}\n"
        f"Время: {now.strftime('%H:%M:%S')}\n"
        f"День недели: {now.strftime('%A')}\n"
        f"Часовой пояс: {timezone_name}\n"
        f"UTC-смещение: {now.strftime('%z')}\n"
        f"ISO 8601: {now.isoformat()}"
    )