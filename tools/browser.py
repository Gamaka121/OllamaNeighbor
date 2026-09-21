import webbrowser


def open_browser(url):
    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    webbrowser.open(url)

    return f"Открыт сайт: {url}"
