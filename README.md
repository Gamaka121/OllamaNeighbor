# Ollama Neighbor

Локальный desktop-ассистент на CustomTkinter и Ollama для Windows.

## Запуск

1. Установите Python 3.11–3.13 и Ollama, затем загрузите модель `qwen3:8b`.
2. В PowerShell из папки проекта выполните:

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Если команда `py -3.13` недоступна, используйте установленную версию Python
вместо неё. Файл `venv` не переносится между компьютерами: его всегда нужно
создавать заново.

## Проверки

```powershell
.\venv\Scripts\python.exe -m compileall -q main.py tools
```

`test_windows.py` — только ручная проверка интеграции с Блокнотом; она не
предназначена для CI и запускается отдельно.
