import json
import logging
import os
import re
import sys
import time
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
FB_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
FB_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
FB_STATE_FILE = Path(os.getenv("FB_STATE_FILE", "data/posted_facebook_ids.json"))
FB_API_VERSION = os.getenv("FB_API_VERSION", "v21.0")
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
POST_DELAY_SECONDS = int(os.getenv("POST_DELAY_SECONDS", "300"))
ENABLE_PHOTOCARD = os.getenv("ENABLE_PHOTOCARD", "true").lower() == "true"
EXCLUDED_SOURCES = {
    s.strip().lower()
    for s in os.getenv("EXCLUDED_SOURCES", "কালবেলা,kalbela").split(",")
    if s.strip()
}

card_generator = None
if ENABLE_PHOTOCARD:
    try:
        from demo_forc_card_gen.photocard_generator import PhotocardGenerator
        card_generator = PhotocardGenerator()
        log.info("[Photocard] PhotocardGenerator initialized successfully.")
    except Exception as exc:
        log.warning("[Photocard] Could not initialize PhotocardGenerator (%s); falling back to raw images.", exc)

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
    # Fetch at least 2 pages (or 2x MAX_NEWS_PER_RUN) to account for previously posted items
    fetch_target = max(MAX_NEWS_PER_RUN * 2, 40)

    while url and len(collected) < fetch_target:
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

    return collected


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
        article_url = f"/newsDetails/{slug}/"

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
        "source": item.get("source") or {},
    }


def load_state(file_path=STATE_FILE):
    if not file_path.exists():
        return {"posted_ids": []}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if not isinstance(data.get("posted_ids"), list):
            return {"posted_ids": []}
        return data
    except (json.JSONDecodeError, OSError):
        log.warning("State file %s unreadable; starting with empty state.", file_path)
        return {"posted_ids": []}


def save_state(state, file_path=STATE_FILE):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp = file_path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(file_path)


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


def telegram_post(endpoint, payload=None, files=None):
    response = session.post(
        endpoint,
        data=payload,
        files=files,
        timeout=REQUEST_TIMEOUT
    )
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
    photocard = article.get("photocard_path")
    has_local_card = photocard and os.path.exists(photocard)
    image_url = article.get("image")

    if not has_local_card and not image_url:
        log.info("Article %s has neither photocard nor image; posting text-only.", article["id"])
        return telegram_send_message(article)

    endpoint = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    caption = build_caption(article)

    if DRY_RUN:
        log.info(
            "[DRY RUN] Would publish article %s: %s (card=%s, img=%s)",
            article["id"],
            article["title"],
            bool(has_local_card),
            bool(image_url),
        )
        return {"message_id": f"dry-run-{article['id']}"}

    payload = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "HTML",
    }

    try:
        if has_local_card:
            with open(photocard, "rb") as f:
                files = {"photo": (Path(photocard).name, f, "image/png")}
                return telegram_post(endpoint, payload, files=files)
        else:
            payload["photo"] = image_url
            return telegram_post(endpoint, payload)
    except Exception as exc:
        log.warning(
            "sendPhoto failed for article %s (%s); attempting text-only fallback...",
            article["id"],
            exc,
        )
        return telegram_send_message(article)


def build_facebook_caption(article):
    title = article["title"]
    desc = clean_description(article["description"], limit=1500)
    link = article["url"]

    parts = [title]
    if desc:
        parts.append(desc)
    parts.append(f"বিস্তারিত পড়ুন: {link}")
    parts.append("#Khobornama #BangladeshNews")
    return "\n\n".join(parts)



def facebook_post(endpoint, payload=None, files=None):
    response = session.post(
        endpoint,
        data=payload,
        files=files,
        timeout=REQUEST_TIMEOUT
    )

    try:
        data = response.json()
    except Exception:
        log.error(
            "Facebook returned non-JSON (%s): %s",
            response.status_code,
            response.text[:500]
        )
        response.raise_for_status()
        raise

    if "error" in data:
        err = data["error"]
        msg = err.get("message", "Unknown Facebook error")
        code = err.get("code", response.status_code)
        subcode = err.get("error_subcode", "")

        full_err = (
            f"{code} (subcode {subcode}): {msg}"
            if subcode else f"{code}: {msg}"
        )

        log.error("Facebook API Error: %s", full_err)
        raise RuntimeError(full_err)

    response.raise_for_status()
    return data


def facebook_publish_article(article):
    caption = build_facebook_caption(article)

    if DRY_RUN:
        log.info(
            "[DRY RUN][FB] Would publish article %s: %s",
            article["id"],
            article["title"]
        )
        return {"id": f"dry-run-fb-{article['id']}"}

    photocard = article.get("photocard_path")
    has_local_card = photocard and os.path.exists(photocard)
    image_url = article.get("image")

    # Step 1: Upload image as unpublished photo (local photocard or remote image URL)
    if has_local_card or image_url:
        photo_endpoint = (
            f"https://graph.facebook.com/"
            f"{FB_API_VERSION}/{FB_PAGE_ID}/photos"
        )

        if has_local_card:
            photo_payload = {
                "published": "false",
                "access_token": FB_ACCESS_TOKEN,
            }
            with open(photocard, "rb") as f:
                photo_files = {
                    "source": (Path(photocard).name, f, "image/png")
                }
                photo_result = facebook_post(
                    photo_endpoint,
                    payload=photo_payload,
                    files=photo_files
                )
        else:
            photo_payload = {
                "url": image_url,
                "published": "false",
                "access_token": FB_ACCESS_TOKEN,
            }
            photo_result = facebook_post(
                photo_endpoint,
                payload=photo_payload
            )

        photo_id = photo_result.get("id")

        if not photo_id:
            raise RuntimeError(
                f"Facebook image upload returned no photo ID: {photo_result}"
            )

        log.info(
            "[Facebook] Image uploaded successfully. Photo ID=%s",
            photo_id
        )

        # Step 2: Create an actual Page Feed post with the photo
        feed_endpoint = (
            f"https://graph.facebook.com/"
            f"{FB_API_VERSION}/{FB_PAGE_ID}/feed"
        )

        feed_payload = {
            "message": caption,
            "attached_media[0]": json.dumps({
                "media_fbid": photo_id
            }),
            "published": "true",
            "access_token": FB_ACCESS_TOKEN,
        }

        result = facebook_post(
            feed_endpoint,
            payload=feed_payload
        )

        post_id = result.get("id")

        if not post_id:
            raise RuntimeError(
                f"Facebook Feed returned no post ID: {result}"
            )

        log.info(
            "[Facebook] Page Feed post published successfully. "
            "Post ID=%s | Photo ID=%s",
            post_id,
            photo_id
        )

        return result

    # Step 3: Text/link post when no image is available
    feed_endpoint = (
        f"https://graph.facebook.com/"
        f"{FB_API_VERSION}/{FB_PAGE_ID}/feed"
    )

    feed_payload = {
        "message": caption,
        "link": article["url"],
        "published": "true",
        "access_token": FB_ACCESS_TOKEN,
    }

    result = facebook_post(feed_endpoint, payload=feed_payload)

    log.info(
        "[Facebook] Text/link post published. Post ID=%s",
        result.get("id")
    )

    return result


def publish_all_channels(normalized_articles):
    tg_enabled = bool(BOT_TOKEN and CHAT_ID)
    fb_enabled = bool(FB_PAGE_ID and FB_ACCESS_TOKEN)

    if not tg_enabled and not fb_enabled:
        log.info("Neither Telegram nor Facebook credentials configured; nothing to publish.")
        return 0

    if tg_enabled:
        masked_token = (BOT_TOKEN[:6] + "..." + BOT_TOKEN[-4:]) if len(BOT_TOKEN) > 10 else "(too short)"
        log.info("[Telegram] Configured: CHAT_ID=%s | BOT_TOKEN=%s", CHAT_ID, masked_token)
    else:
        log.info("[Telegram] BOT_TOKEN or CHAT_ID not set; skipping Telegram.")

    if fb_enabled:
        masked_fb_token = (FB_ACCESS_TOKEN[:6] + "..." + FB_ACCESS_TOKEN[-4:]) if len(FB_ACCESS_TOKEN) > 10 else "(too short)"
        log.info("[Facebook] Configured: PAGE_ID=%s | TOKEN=%s", FB_PAGE_ID, masked_fb_token)
    else:
        log.info("[Facebook] FACEBOOK_PAGE_ID or FACEBOOK_PAGE_ACCESS_TOKEN not set; skipping Facebook.")

    tg_state = load_state(STATE_FILE) if tg_enabled else {"posted_ids": []}
    fb_state = load_state(FB_STATE_FILE) if fb_enabled else {"posted_ids": []}

    tg_posted = set(str(x) for x in tg_state.get("posted_ids", []))
    fb_posted = set(str(x) for x in fb_state.get("posted_ids", []))

    log.info(
        "Loaded states: Telegram has %d posted IDs, Facebook has %d posted IDs.",
        len(tg_posted),
        len(fb_posted),
    )

    # Collect articles that need to be published in at least one active channel
    new_articles = []
    for a in normalized_articles:
        needs_tg = tg_enabled and (a["id"] not in tg_posted)
        needs_fb = fb_enabled and (a["id"] not in fb_posted)
        if needs_tg or needs_fb:
            new_articles.append(a)

    new_articles.reverse()

    total_new = len(new_articles)
    if total_new > MAX_NEWS_PER_RUN:
        log.info(
            "Found %d new articles across channels; capping to oldest %d for this run.",
            total_new,
            MAX_NEWS_PER_RUN,
        )
        new_articles = new_articles[:MAX_NEWS_PER_RUN]

    log.info(
        "Publishing up to %d articles in this run (delay between posts: %d seconds / %.1f mins).",
        len(new_articles),
        POST_DELAY_SECONDS,
        POST_DELAY_SECONDS / 60,
    )

    # 1. Photocard generation: 1st 10 in Design 0 (Jamuna), next 10 in Design 1 (Somoy)
    if card_generator:
        for idx, article in enumerate(new_articles):
            if article.get("photocard_path") and os.path.exists(article["photocard_path"]):
                continue
            design_idx = 0 if idx < 10 else 1
            try:
                card_path = card_generator.generate_card(article, design=design_idx)
                article["photocard_path"] = str(card_path)
                article["photocard_design"] = design_idx
                log.info(
                    "[Photocard][%d/%d] Generated card for article=%s design=%d (%s)",
                    idx + 1,
                    len(new_articles),
                    article["id"],
                    design_idx,
                    card_path,
                )
            except Exception as exc:
                log.warning(
                    "[Photocard] Failed generating card for article=%s (design %d): %s",
                    article["id"],
                    design_idx,
                    exc,
                )

    # 2. Sequential posting across channels with delay between articles
    success_tg = 0
    success_fb = 0

    for idx, article in enumerate(new_articles):
        art_id = article["id"]
        log.info(
            "[Post][%d/%d] Publishing article=%s: %s",
            idx + 1,
            len(new_articles),
            art_id,
            article["title"],
        )

        # Publish to Telegram
        if tg_enabled and (art_id not in tg_posted):
            try:
                tg_result = telegram_publish_article(article)
                if DRY_RUN:
                    log.info("[DRY RUN][Telegram] Published article=%s", art_id)
                else:
                    tg_posted.add(art_id)
                    tg_state["posted_ids"] = sorted(tg_posted)
                    save_state(tg_state, STATE_FILE)
                    success_tg += 1
                    msg_id = tg_result.get("message_id") if isinstance(tg_result, dict) else None
                    log.info("[Telegram][%d/%d] Success article=%s msg_id=%s", idx + 1, len(new_articles), art_id, msg_id)
            except Exception as exc:
                log.exception("[Telegram] Failed article=%s: %s", art_id, exc)

        # Publish to Facebook
        if fb_enabled and (art_id not in fb_posted):
            try:
                fb_result = facebook_publish_article(article)
                if DRY_RUN:
                    log.info("[DRY RUN][Facebook] Published article=%s", art_id)
                else:
                    fb_posted.add(art_id)
                    fb_state["posted_ids"] = sorted(fb_posted)
                    save_state(fb_state, FB_STATE_FILE)
                    success_fb += 1
                    post_id = fb_result.get("id") if isinstance(fb_result, dict) else None
                    log.info("[Facebook][%d/%d] Success article=%s post_id=%s", idx + 1, len(new_articles), art_id, post_id)
            except Exception as exc:
                log.exception("[Facebook] Failed article=%s: %s", art_id, exc)

        # Interval between posts (5 minutes by default)
        if idx < len(new_articles) - 1 and not DRY_RUN:
            log.info(
                "Waiting %d seconds (%.1f minutes) before publishing article %d/%d...",
                POST_DELAY_SECONDS,
                POST_DELAY_SECONDS / 60,
                idx + 2,
                len(new_articles),
            )
            time.sleep(POST_DELAY_SECONDS)

    log.info(
        "Finished multi-channel publication. Processed=%d | Telegram new=%d | Facebook new=%d",
        len(new_articles),
        success_tg,
        success_fb,
    )
    return max(success_tg, success_fb)


def main():
    log.info("=== Starting Khobornama Multi-Channel Auto Publisher ===")
    log.info(
        "Config: DRY_RUN=%s | MAX_NEWS_PER_RUN=%d | POST_DELAY_SECONDS=%d | API_BASE_URL=%s | NEWS_ENDPOINT=%s",
        DRY_RUN,
        MAX_NEWS_PER_RUN,
        POST_DELAY_SECONDS,
        API_BASE_URL,
        NEWS_ENDPOINT,
    )

    articles = fetch_news()
    log.info("Fetched %d news items from %s", len(articles), API_BASE_URL + NEWS_ENDPOINT)

    normalized = []
    skipped_sources = 0
    for raw in articles:
        article = article_fields(raw)
        if not article["id"]:
            log.warning("Skipping item without id: %s", raw)
            continue
        source_data = article.get("source") or {}
        source_name = (
            source_data.get("name", "") if isinstance(source_data, dict) else str(source_data)
        ).strip().lower()
        if source_name and any(ex in source_name for ex in EXCLUDED_SOURCES):
            skipped_sources += 1
            continue
        normalized.append(article)

    if skipped_sources:
        log.info("Skipped %d articles from excluded sources (%s).", skipped_sources, ", ".join(sorted(EXCLUDED_SOURCES)))

    publish_all_channels(normalized)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"::error title=Automation Failure::{exc}", flush=True)
        log.error("Automation failed: %s", exc)
        sys.exit(1)
