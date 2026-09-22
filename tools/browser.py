import webbrowser
from urllib.parse import urlparse


def open_browser(url):
    url = str(url or "").strip()
    if not url:
        return {"success": False, "error": "Не указан адрес сайта."}

    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {"success": False, "error": "Разрешены только корректные HTTP(S)-адреса."}

    opened = webbrowser.open(url)

    if not opened:
        return {"success": False, "error": "Windows не приняла команду открыть браузер.", "data": {"url": url}}
    return {"success": True, "message": "Команда открытия сайта передана браузеру.", "data": {"url": url}}
