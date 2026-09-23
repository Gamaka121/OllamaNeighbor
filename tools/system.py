"""
tools/system.py — информация о локальном компьютере.
"""

from datetime import datetime

import platform
import psutil


WEEKDAYS_RU = (
    "Понедельник", "Вторник", "Среда", "Четверг",
    "Пятница", "Суббота", "Воскресенье"
)


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
    """Возвращает текущие процессы, отсортированные по потреблению ОЗУ.

    Это read-only системный запрос. Для вопросов вроде
    «что больше всего жрёт/использует ОЗУ», «какая программа съедает память»,
    «что больше всего потребляет оперативку» результатом top_process является
    первый и наиболее важный ответ.
    """
    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "memory_percent", "memory_info"]
    ):
        try:
            info = process.info
            memory_percent = float(info.get("memory_percent") or 0)
            name = info.get("name") or "<без имени>"
            pid = info.get("pid")
            memory_info = info.get("memory_info")
            rss_bytes = int(getattr(memory_info, "rss", 0) or 0)

            processes.append(
                (
                    memory_percent,
                    pid,
                    name,
                    rss_bytes,
                )
            )

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    processes.sort(key=lambda item: item[0], reverse=True)

    if not processes:
        return {
            "success": False,
            "error": "Не удалось получить список процессов."
        }

    top = processes[:15]
    top_process = top[0]

    return {
        "success": True,
        "top_process": {
            "name": top_process[2],
            "pid": top_process[1],
            "memory_percent": round(top_process[0], 1),
            "memory_mb": round(top_process[3] / (1024 ** 2), 1),
        },
        "processes": [
            {
                "name": name,
                "pid": pid,
                "memory_percent": round(memory, 1),
                "memory_mb": round(rss_bytes / (1024 ** 2), 1),
            }
            for memory, pid, name, rss_bytes in top
        ],
    }


def get_current_datetime():
    """
    Возвращает текущие дату, время и часовой пояс
    непосредственно с компьютера пользователя.

    Каждый вызов получает новое значение.
    Интернет и memory.json здесь не используются.
    """

    now = datetime.now().astimezone()
    weekday_ru = WEEKDAYS_RU[now.weekday()]
    timezone_name = now.tzname() or "локальный"

    return (
        "ТЕКУЩИЕ ДАТА И ВРЕМЯ КОМПЬЮТЕРА\n"
        f"Дата: {now.strftime('%d.%m.%Y')}\n"
        f"Время: {now.strftime('%H:%M:%S')}\n"
        f"День недели: {weekday_ru}\n"
        f"Часовой пояс: {timezone_name}\n"
        f"UTC-смещение: {now.strftime('%z')}\n"
        f"ISO 8601: {now.isoformat()}"
    )
