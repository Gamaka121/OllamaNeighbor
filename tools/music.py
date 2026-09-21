"""Воспроизведение конкретного трека в YouTube Music."""

from __future__ import annotations

import json
import re
import webbrowser
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

REQUEST_TIMEOUT = 12

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
VIDEO_ID_IN_TEXT_RE = re.compile(r"[A-Za-z0-9_-]{11}")

WATCH_URL_RE = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|music\.youtube\.com/watch\?v=)"
    r"([A-Za-z0-9_-]{11})"
)

INNERTUBE_SEARCH_URL = (
    "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
)

DDG_HTML_URL = "https://html.duckduckgo.com/html/"


def _session():
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        }
    )
    return session


def _http(method: str, url: str, **kwargs):
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    session = _session()

    try:
        return session.request(method, url, **kwargs)
    except requests.exceptions.SSLError:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        kwargs["verify"] = False
        return session.request(method, url, **kwargs)


def _clean_query(*parts: str) -> str:
    return " ".join(str(part or "").strip() for part in parts).strip()


def _extract_video_id(value: str) -> str | None:
    text = (value or "").strip()

    if VIDEO_ID_RE.fullmatch(text):
        return text

    match = WATCH_URL_RE.search(text)
    if match:
        return match.group(1)

    try:
        parsed = urlparse(text)
    except Exception:
        return None

    if parsed.netloc and "youtube" in parsed.netloc.lower():
        video_id = parse_qs(parsed.query).get("v", [None])[0]
        if video_id and VIDEO_ID_RE.fullmatch(video_id):
            return video_id

        if parsed.path.startswith("/"):
            tail = parsed.path.strip("/").split("/")[-1]
            if VIDEO_ID_RE.fullmatch(tail):
                return tail

    return None


def _collect_video_ids(payload) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def walk(node) -> None:
        if isinstance(node, dict):
            video_id = node.get("videoId")
            if (
                isinstance(video_id, str)
                and VIDEO_ID_RE.fullmatch(video_id)
                and video_id not in seen
                and "reelWatchEndpoint" not in node
            ):
                seen.add(video_id)
                found.append(video_id)

            for value in node.values():
                walk(value)

        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    return found


def _search_youtube_innertube(query: str) -> str | None:
    try:
        response = _http(
            "POST",
            INNERTUBE_SEARCH_URL,
            json={
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20240815.00.00",
                        "hl": "ru",
                        "gl": "RU",
                    }
                },
                "query": query,
            },
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        return None

    ids = _collect_video_ids(payload)
    return ids[0] if ids else None


def _search_youtube_html(query: str) -> str | None:
    url = (
        "https://www.youtube.com/results?search_query="
        + quote_plus(query)
        + "&sp=EgIQAQ%3D%3D"
    )

    try:
        response = _http("GET", url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    html = response.text
    initial = re.search(
        r"ytInitialData\s*=\s*(\{.+?\});\s*</script>",
        html,
        re.DOTALL,
    )
    if initial:
        try:
            payload = json.loads(initial.group(1))
            ids = _collect_video_ids(payload)
            if ids:
                return ids[0]
        except json.JSONDecodeError:
            pass

    match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
    return match.group(1) if match else None


def _unwrap_ddg_url(href: str) -> str:
    href = (href or "").strip()
    if not href:
        return href

    try:
        parsed = urlparse(href)
        if "duckduckgo.com" in (parsed.netloc or "").lower():
            target = parse_qs(parsed.query).get("uddg", [None])[0]
            if target:
                return unquote(target)
    except Exception:
        return href

    return href


def _search_duckduckgo(query: str) -> str | None:
    try:
        response = _http(
            "POST",
            DDG_HTML_URL,
            data={"q": f"{query} site:youtube.com/watch"},
        )
        response.raise_for_status()
    except requests.RequestException:
        return None

    for match in re.finditer(r'href="([^"]+)"', response.text):
        href = _unwrap_ddg_url(match.group(1).replace("&amp;", "&"))
        video_id = _extract_video_id(href)
        if video_id:
            return video_id

    for match in WATCH_URL_RE.finditer(unquote(response.text)):
        return match.group(1)

    return None


def _find_video_id(query: str) -> str | None:
    direct = _extract_video_id(query)
    if direct:
        return direct

    for searcher in (
        _search_youtube_innertube,
        _search_youtube_html,
        _search_duckduckgo,
    ):
        video_id = searcher(query)
        if video_id:
            return video_id

    return None


def play_yt_music(query: str, artist: str = "") -> str:
    """Ищет трек и открывает его в YouTube Music."""

    track = _clean_query(query)
    performer = _clean_query(artist)

    if not track:
        return "Не указано название трека."

    search_query = _clean_query(performer, track)
    video_id = _find_video_id(search_query)

    if not video_id and performer:
        video_id = _find_video_id(track)

    if video_id:
        url = (
            "https://music.youtube.com/watch?v="
            + video_id
            + "&autoplay=1"
        )
        webbrowser.open(url)
        label = f"{performer} — {track}" if performer else track
        return (
            f"Открыт трек «{label}» в YouTube Music:\n"
            f"{url}"
        )

    fallback = (
        "https://music.youtube.com/search?q="
        + quote_plus(search_query)
    )
    webbrowser.open(fallback)
    return (
        f"Не удалось найти точную ссылку на трек «{search_query}». "
        f"Открыт поиск YouTube Music:\n{fallback}"
    )
