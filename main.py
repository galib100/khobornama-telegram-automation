import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("khobornama-telegram")

API_BASE_URL = (os.getenv("API_BASE_URL") or "https://api.khobornama.info.bd/api/").rstrip("/") + "/"
NEWS_ENDPOINT = (os.getenv("NEWS_ENDPOINT") or "news/").lstrip("/")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
SITE_BASE_URL = (os.getenv("SITE_BASE_URL") or "https://khobornama.info.bd").rstrip("/")
API_ORIGIN = f"{urlparse(API_BASE_URL).scheme}://{urlparse(API_BASE_URL).netloc}"
MAX_NEWS_PER_RUN = int(os.getenv("MAX_NEWS_PER_RUN", "30"))
STATE_FILE = Path(os.getenv("STATE_FILE", "data/posted_ids.json"))
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))

session = requests.Session()
session.headers.update({"User-Agent": "KhobornamaTelegramPublisher/1.0"})


def get_json(url, params=None):
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def find_list(payload):
    """Accept common DRF and plain-list response shapes."""
    if isinstance(payload, list):
        return payload, None
    if not isinstance(payload, dict):
        raise ValueError("Unexpected API response: expected a JSON object or list")

    for key in ("results", "data", "news", "articles"):
        value = payload.get(key)
        if isinstance(value, list):
            return value, payload.get("next")

    # Some APIs wrap a list one level deeper.
    for value in payload.values():
        if isinstance(value, dict):
            try:
                items, next_url = find_list(value)
                if items is not None:
                    return items, next_url
            except ValueError:
                pass

    raise ValueError(
        "Could not find a news list in API response. "
        "Set NEWS_ENDPOINT and adapt find_list() to the actual API schema."
    )


def fetch_news():
    url = urljoin(API_BASE_URL, NEWS_ENDPOINT)
    collected = []
    seen_pages = set()

    while url and len(collected) < MAX_NEWS_PER_RUN:
        if url in seen_pages:
            log.warning("Pagination loop detected; stopping.")
            break
        seen_pages.add(url)

        payload = get_json(url)
        items, next_url = find_list(payload)
        collected.extend(items)

        if not next_url:
            break
        url = urljoin(API_BASE_URL, next_url)

    return collected[:MAX_NEWS_PER_RUN]


def first_value(item, *keys):
    for key in keys:
        value = item.get(key)
        if value not in (None, ""):
            return value
    return ""


def absolute_url(value):
    if not value:
        return ""
    return urljoin(SITE_BASE_URL + "/", str(value))


def article_fields(item):
    article_id = first_value(item, "id", "pk", "news_id", "article_id")
    title = first_value(item, "title", "headline", "name")
    description = first_value(
        item, "short_description", "summary", "excerpt", "description", "content"
    )
    image = first_value(
        item, "featured_image", "image", "thumbnail", "cover_image", "banner"
    )
    article_url = first_value(item, "url", "absolute_url", "link")
    slug = first_value(item, "slug")

    # DRF image fields may be objects such as {"url": "..."}.
    if isinstance(image, dict):
        image = image.get("url", "")

    if not article_url and slug:
        article_url = f"/news/{slug}/"

    return {
        "id": str(article_id) if article_id is not None else "",
        "title": str(title or "খবরনামা"),
        "description": str(description or ""),
        "image": (
            urljoin(API_ORIGIN + "/", str(image).lstrip("/"))
            if image and not str(image).startswith(("http://", "https://"))
            else str(image or "")
        ),
        "url": absolute_url(article_url) if article_url else SITE_BASE_URL,
        "published_at": first_value(item, "published_at", "created_at", "date"),
    }


def load_state():
    if not STATE_FILE.exists():
        return {"posted_ids": []}
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data.get("posted_ids"), list):
            return {"posted_ids": []}
        return data
    except (json.JSONDecodeError, OSError):
        log.warning("State file unreadable; starting with empty state.")
        return {"posted_ids": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def clean_description(value, limit=450):
    # Remove HTML tags and collapse whitespace before escaping for Telegram HTML.
    value = re.sub(r"<[^>]*>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    if len(value) > limit:
        value = value[: limit - 1].rsplit(" ", 1)[0] + "…"
    return value


def build_caption(article):
    title = escape(article["title"])
    description = escape(clean_description(article["description"]))
    link = escape(article["url"], quote=True)
    caption = (
        f"<b>{title}</b>\n\n"
        f"{description}\n\n"
        f'🔗 <a href="{link}">বিস্তারিত পড়ুন</a>\n\n'
        f"#Khobornama #BangladeshNews"
    )
    # Telegram sendPhoto caption limit is 1024 characters.
    if len(caption) > 1024:
        remaining = max(80, 1024 - len(title) - len(link) - 100)
        description = escape(clean_description(article["description"], remaining))
        caption = (
            f"<b>{title}</b>\n\n{description}\n\n"
            f'🔗 <a href="{link}">বিস্তারিত পড়ুন</a>\n\n'
            f"#Khobornama #BangladeshNews"
        )
    if len(caption) > 1024:
        caption = f"<b>{title[:250]}</b>\n\n🔗 <a href=\"{link}\">বিস্তারিত পড়ুন</a>"
    return caption


def telegram_post(endpoint, payload):
    response = session.post(endpoint, data=payload, timeout=REQUEST_TIMEOUT)
    try:
        data = response.json()
    except Exception:
        log.error("Telegram endpoint returned non-JSON (%s): %s", response.status_code, response.text[:200])
        response.raise_for_status()
        raise

    if not data.get("ok"):
        desc = data.get("description", "Unknown Telegram error")
        error_code = data.get("error_code", response.status_code)
        print(f"::error title=Telegram API Error::{error_code} - {desc}", flush=True)
        log.error("Telegram API Error [%s]: %s", error_code, desc)
        raise RuntimeError(f"Telegram API Error [{error_code}]: {desc}")
    return data["result"]


def telegram_send_message(article):
    endpoint = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": build_caption(article),
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    if DRY_RUN:
        log.info("[DRY RUN] Would publish text-only article %s: %s", article["id"], article["title"])
        return {"message_id": f"dry-run-{article['id']}"}

    return telegram_post(endpoint, payload)


def telegram_publish_article(article):
    if not article.get("image"):
        log.info("Article %s has no featured image; posting text-only.", article["id"])
        return telegram_send_message(article)

    endpoint = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": article["image"],
        "caption": build_caption(article),
        "parse_mode": "HTML",
    }
    if DRY_RUN:
        log.info("[DRY RUN] Would publish article %s: %s", article["id"], article["title"])
        return {"message_id": f"dry-run-{article['id']}"}

    try:
        return telegram_post(endpoint, payload)
    except Exception as exc:
        log.warning(
            "sendPhoto failed for article %s (%s); attempting text-only fallback...",
            article["id"],
            exc,
        )
        return telegram_send_message(article)


def main():
    log.info("=== Starting Khobornama Telegram Publisher ===")
    log.info(
        "Config: DRY_RUN=%s | MAX_NEWS_PER_RUN=%d | API_BASE_URL=%s | NEWS_ENDPOINT=%s",
        DRY_RUN,
        MAX_NEWS_PER_RUN,
        API_BASE_URL,
        NEWS_ENDPOINT,
    )

    if not BOT_TOKEN:
        print("::error title=Missing Secret::TELEGRAM_BOT_TOKEN environment variable is not set or empty.", flush=True)
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set or empty.")
    if not CHAT_ID:
        print("::error title=Missing Secret::TELEGRAM_CHAT_ID environment variable is not set or empty.", flush=True)
        raise ValueError("TELEGRAM_CHAT_ID environment variable is not set or empty.")

    masked_token = (BOT_TOKEN[:6] + "..." + BOT_TOKEN[-4:]) if len(BOT_TOKEN) > 10 else "(too short)"
    print(f"::notice title=Config Info::CHAT_ID={CHAT_ID} | BOT_TOKEN={masked_token} (len={len(BOT_TOKEN)})", flush=True)
    log.info("Credentials check: CHAT_ID=%s | BOT_TOKEN=%s (length=%d)", CHAT_ID, masked_token, len(BOT_TOKEN))

    state = load_state()
    posted = set(str(x) for x in state["posted_ids"])
    log.info("Loaded state: %d previously posted article IDs.", len(posted))

    articles = fetch_news()
    log.info("Fetched %d news items from %s", len(articles), API_BASE_URL + NEWS_ENDPOINT)

    normalized = []
    for raw in articles:
        article = article_fields(raw)
        if not article["id"]:
            log.warning("Skipping item without id: %s", raw)
            continue
        normalized.append(article)

    # Publish oldest first so a batch of newly discovered articles appears chronologically.
    new_articles = [a for a in normalized if a["id"] not in posted]
    new_articles.reverse()

    log.info("Found %d new articles to publish.", len(new_articles))

    success_count = 0
    for article in new_articles:
        try:
            result = telegram_publish_article(article)
            if DRY_RUN:
                log.info("[DRY RUN] Not recording article=%s as posted.", article["id"])
                continue
            posted.add(article["id"])
            success_count += 1
            log.info("Published article=%s telegram_message_id=%s", article["id"], result.get("message_id"))
            state["posted_ids"] = sorted(posted)
            save_state(state)
        except Exception:
            log.exception("Failed to publish article=%s title=%s", article["id"], article["title"])
            # Stop at the first failure to preserve chronological order and retry next run.
            raise

    log.info("Finished. New=%d published=%d already_posted=%d",
             len(new_articles), success_count, len(normalized) - len(new_articles))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"::error title=Automation Failure::{exc}", flush=True)
        log.error("Automation failed: %s", exc)
        sys.exit(1)
