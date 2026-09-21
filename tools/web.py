"""
tools/web.py — доступ в интернет для Ollama Neighbor.

Инструменты:

    web_search(query, max_results=5)
        Поиск через DuckDuckGo HTML.

    read_webpage(url, max_chars=6000)
        Чтение очищенного текста веб-страницы.

Вспомогательно:

    extract_links(url, max_links=20)

Требуются:
    requests
    beautifulsoup4
    lxml
"""

import re

from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


# ============================================================
# НАСТРОЙКИ
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 12

DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_CHARS = 6000

DDG_HTML_URL = "https://html.duckduckgo.com/html/"


# ============================================================
# ЗАЩИТА URL
# ============================================================

BLOCKED_HOST_PATTERNS = (
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "169.254.",
    "10.",
    "192.168.",
)


def _session():
    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
    )

    return session


def _is_blocked_url(url):
    """
    Базовая SSRF-защита.

    Разрешаем только http/https.
    Блокируем localhost и типичные приватные адреса.
    """

    try:
        parsed = urlparse(url)

    except Exception:
        return True

    if parsed.scheme not in ("http", "https"):
        return True

    host = (parsed.hostname or "").lower()

    if not host:
        return True

    for pattern in BLOCKED_HOST_PATTERNS:

        if host == pattern or host.startswith(pattern):
            return True

    return False


# ============================================================
# TEXT CLEANUP
# ============================================================

def _clean_text(text):
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# WEB SEARCH
# ============================================================

def web_search(
    query,
    max_results=DEFAULT_MAX_RESULTS,
):
    """
    Ищет информацию через DuckDuckGo.

    Возвращает заголовки, URL и краткие описания.
    """

    query = (query or "").strip()

    if not query:
        return "Пустой поисковый запрос."

    try:
        max_results = int(max_results)

    except (TypeError, ValueError):
        max_results = DEFAULT_MAX_RESULTS

    max_results = max(
        1,
        min(max_results, 10),
    )

    try:
        session = _session()

        response = session.post(
            DDG_HTML_URL,
            data={"q": query},
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        return f"Ошибка поиска: {error}"

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    results = []

    for block in soup.select("div.result"):

        link_tag = block.select_one(
            "a.result__a"
        )

        if link_tag is None:
            continue

        title = link_tag.get_text(
            strip=True
        )

        href = link_tag.get(
            "href",
            "",
        )

        if not title or not href:
            continue

        snippet_tag = block.select_one(
            ".result__snippet"
        )

        snippet = (
            snippet_tag.get_text(
                strip=True
            )
            if snippet_tag is not None
            else ""
        )

        results.append(
            {
                "title": title,
                "url": href,
                "snippet": snippet,
            }
        )

        if len(results) >= max_results:
            break

    if not results:
        return (
            f"По запросу «{query}» "
            "ничего не найдено."
        )

    lines = [
        f"Результаты поиска по запросу "
        f"«{query}»:\n"
    ]

    for index, item in enumerate(
        results,
        start=1,
    ):
        lines.append(
            f"{index}. {item['title']}"
        )

        lines.append(
            f"   {item['url']}"
        )

        if item["snippet"]:
            lines.append(
                f"   {item['snippet']}"
            )

        lines.append("")

    return "\n".join(lines).strip()


# ============================================================
# WEBPAGE PARSING
# ============================================================

STRIP_TAGS = (
    "script",
    "style",
    "noscript",
    "svg",
    "form",
    "iframe",
    "nav",
    "footer",
    "header",
    "aside",
)


NOISE_PATTERNS = (
    "sidebar",
    "related",
    "also-read",
    "also_read",
    "read-also",
    "readalso",
    "recommend",
    "rec-",
    "teaser",
    "promo",
    "banner",
    "advert",
    " ad-",
    "-ad-",
    "share",
    "social",
    "similar",
    "popular",
    "trending",
    "further-reading",
    "you-may-like",
    "также-читают",
    "также_читают",
    "рекоменд",
    "популярн",
    "читайте-также",
)


def _strip_noise_blocks(soup):
    """
    Удаляет типичные рекламные и рекомендательные блоки.
    """

    for tag in soup.find_all(
        ["div", "section", "ul"]
    ):

        if getattr(
            tag,
            "attrs",
            None,
        ) is None:
            continue

        classes = tag.get(
            "class",
            [],
        ) or []

        tag_id = tag.get(
            "id",
            "",
        ) or ""

        attrs_text = " ".join(
            [
                " ".join(classes),
                tag_id,
            ]
        ).lower()

        if any(
            pattern in attrs_text
            for pattern in NOISE_PATTERNS
        ):
            try:
                tag.decompose()

            except Exception:
                pass


def _main_content(soup):
    """
    Сначала пытаемся найти основной контент.
    """

    for selector in (
        "main",
        "article",
    ):

        candidate = soup.find(
            selector
        )

        if (
            candidate is not None
            and candidate.get_text(
                strip=True
            )
        ):
            return candidate

    return soup.body or soup


# ============================================================
# READ WEBPAGE
# ============================================================

def read_webpage(
    url,
    max_chars=DEFAULT_MAX_CHARS,
):
    """
    Скачивает веб-страницу и возвращает
    очищенный читаемый текст.
    """

    url = (url or "").strip()

    if not url:
        return "Не указан адрес страницы."

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    if _is_blocked_url(url):
        return "Этот адрес запрещён к открытию."

    try:
        max_chars = int(max_chars)

    except (TypeError, ValueError):
        max_chars = DEFAULT_MAX_CHARS

    max_chars = max(
        500,
        min(max_chars, 20000),
    )

    try:
        session = _session()

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        response.raise_for_status()

    except requests.RequestException as error:
        return (
            f"Не удалось открыть страницу: "
            f"{error}"
        )

    # Проверяем конечный адрес после redirect.
    if _is_blocked_url(
        response.url
    ):
        return (
            "Страница перенаправила запрос "
            "на запрещённый адрес."
        )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        .lower()
    )

    if (
        "text/html" not in content_type
        and "xml" not in content_type
    ):
        return (
            "Страница не является HTML "
            f"(Content-Type: "
            f"{content_type or 'неизвестен'})."
        )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # Убираем очевидный технический мусор.
    for tag in soup(STRIP_TAGS):

        try:
            tag.decompose()

        except Exception:
            pass

    title_tag = soup.find("title")

    title = (
        title_tag.get_text(
            strip=True
        )
        if title_tag is not None
        else ""
    )

    # Сначала выбираем основной контент.
    content = _main_content(soup)

    # И только внутри него убираем шум.
    _strip_noise_blocks(content)

    text = content.get_text(
        separator="\n"
    )

    text = _clean_text(text)

    # Если эвристика вырезала слишком много,
    # используем менее агрессивный fallback.
    if len(text) < 200:

        fallback = soup.body or soup

        fallback_text = _clean_text(
            fallback.get_text(
                separator="\n"
            )
        )

        if len(fallback_text) > len(text):
            text = fallback_text

    truncated = False

    if len(text) > max_chars:

        text = text[:max_chars]
        truncated = True

    header = (
        f"Страница: {title or url}\n"
        f"Адрес: {response.url}\n\n"
    )

    footer = (
        "\n\n"
        "[Текст обрезан из-за "
        "большого размера страницы.]"
        if truncated
        else ""
    )

    return (
        header
        + text
        + footer
    )


# ============================================================
# EXTRACT LINKS
# ============================================================

def extract_links(
    url,
    max_links=20,
):
    """
    Вспомогательная функция.
    Модель напрямую её не вызывает.
    """

    url = (url or "").strip()

    if not url.startswith(
        ("http://", "https://")
    ):
        url = "https://" + url

    if _is_blocked_url(url):
        return []

    try:
        session = _session()

        response = session.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

        response.raise_for_status()

    except requests.RequestException:
        return []

    if _is_blocked_url(
        response.url
    ):
        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    links = []

    for tag in soup.find_all(
        "a",
        href=True,
    ):

        href = urljoin(
            response.url,
            tag["href"],
        )

        if _is_blocked_url(href):
            continue

        text = tag.get_text(
            strip=True
        )

        if not text:
            continue

        links.append(
            {
                "text": text,
                "url": href,
            }
        )

        if len(links) >= max_links:
            break

    return links