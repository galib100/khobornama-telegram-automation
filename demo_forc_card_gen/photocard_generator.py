#!/usr/bin/env python3
"""
Khobornama Automated Photocard Generator
Ported from Flutter `ShareableNewsCard` to Python.
Supports the 2 primary card styles:
  0 / 'jamuna': Jamuna TV Style (Bold Red Bottom Banner & Footer)
  1 / 'somoy' : Somoy News Style (Gradient Fade + Red Key Headline + Dual Logos)
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import random
import requests

try:
    from .generator_core import get_browser_path, image_to_base64, render_html_to_image
    from .templates import DESIGN_TEMPLATES, DESIGN_NAMES
except (ImportError, ValueError):
    from generator_core import get_browser_path, image_to_base64, render_html_to_image
    from templates import DESIGN_TEMPLATES, DESIGN_NAMES

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("photocard-generator")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOGO_PATH = SCRIPT_DIR / "assets" / "logo.png"
OUTPUT_DIR = SCRIPT_DIR / "output"

API_BASE_URL = (os.getenv("API_BASE_URL") or "https://api.khobornama.info.bd/api/").rstrip("/") + "/"
NEWS_ENDPOINT = (os.getenv("NEWS_ENDPOINT") or "news/").lstrip("/")


class PhotocardGenerator:
    def __init__(self, logo_path=None, browser_path=None):
        self.logo_path = Path(logo_path or DEFAULT_LOGO_PATH)
        if not self.logo_path.exists():
            log.warning(f"Logo not found at {self.logo_path}. Attempting download...")
            self._download_default_logo()
        
        self.logo_b64 = image_to_base64(self.logo_path)
        self.browser_path = browser_path or get_browser_path()
        if not self.browser_path:
            raise RuntimeError("Headless browser (Edge or Chrome) not found for rendering.")
        log.info(f"Using browser: {self.browser_path}")

    def _download_default_logo(self):
        try:
            self.logo_path.parent.mkdir(parents=True, exist_ok=True)
            r = requests.get("https://khobornama.info.bd/khobornamaNewLogo-256.png", timeout=10)
            if r.status_code == 200:
                self.logo_path.write_bytes(r.content)
                log.info(f"Saved default logo to {self.logo_path}")
        except Exception as e:
            log.warning(f"Could not download default logo: {e}")

    def format_date(self, date_val):
        if not date_val:
            return datetime.now().strftime("%Y-%m-%d")
        if isinstance(date_val, str):
            return date_val.split("T")[0]
        if isinstance(date_val, (datetime,)):
            return date_val.strftime("%Y-%m-%d")
        return str(date_val)

    def generate_card(self, article, design=0, output_path=None, card_size=(1080, 1140)):
        """
        Generate a single photocard for the given article dict.
        design: 0 or 1, or name ('jamuna', 'somoy')
        """
        if isinstance(design, str):
            design_key = design.lower()
            if design_key in ("0", "jamuna"):
                design_idx = 0
            elif design_key in ("1", "somoy"):
                design_idx = 1
            else:
                design_idx = 0
        else:
            design_idx = int(design) % len(DESIGN_NAMES)

        template_func = DESIGN_TEMPLATES.get(design_idx, DESIGN_TEMPLATES[0])

        title = article.get("title", "খবরনামা")
        raw_date = article.get("published_at") or article.get("created_at") or article.get("date")
        date_str = self.format_date(raw_date)

        # Source details
        source_data = article.get("source") or {}
        if isinstance(source_data, dict):
            source_name = source_data.get("name", "খবরনামা")
            source_logo_url = source_data.get("logo", "")
        else:
            source_name = str(source_data)
            source_logo_url = ""

        # Article image
        image_url = article.get("image") or article.get("featured_image") or article.get("thumbnail") or ""
        if isinstance(image_url, dict):
            image_url = image_url.get("url", "")

        # Fetch base64 of images
        image_b64 = image_to_base64(image_url) if image_url else self.logo_b64
        source_logo_b64 = image_to_base64(source_logo_url) if source_logo_url else ""

        html = template_func(
            title=title,
            date_str=date_str,
            image_b64=image_b64,
            logo_b64=self.logo_b64,
            source_name=source_name,
            source_logo_b64=source_logo_b64,
        )

        if output_path is None:
            article_id = article.get("id", "sample")
            filename = f"card_{article_id}_design_{design_idx}.png"
            output_path = OUTPUT_DIR / filename

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        render_html_to_image(html, output_path, width=card_size[0], height=card_size[1])
        log.info(f"Generated photocard [{DESIGN_NAMES[design_idx]}]: {output_path}")
        return output_path

    def generate_bulk(self, articles, output_dir=None, design_mode="split_10", card_size=(1080, 1140)):
        """
        Generate photocards in bulk.
        design_mode:
          - 'split_10' or 'split': 1st 10 articles in Design 0 (Jamuna), remaining in Design 1 (Somoy)
          - 'cycle': Alternates between 0 (Jamuna) and 1 (Somoy)
          - 'random': Random choice between 0 (Jamuna) and 1 (Somoy)
          - 'all': Generate both designs for every article
          - 0 or 'jamuna': All Jamuna style
          - 1 or 'somoy': All Somoy style
        """
        out_dir = Path(output_dir or OUTPUT_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        generated = []
        for idx, article in enumerate(articles):
            art_id = article.get("id", f"art_{idx+1}")
            if design_mode in ("split_10", "split"):
                # First 10 in Design 0 (Jamuna), last 10 (or next) in Design 1 (Somoy)
                d = 0 if idx < 10 else 1
                card_path = out_dir / f"card_{art_id}_design_{d}.png"
                self.generate_card(article, design=d, output_path=card_path, card_size=card_size)
                generated.append(card_path)
            elif design_mode == "all":
                for d in range(len(DESIGN_NAMES)):
                    card_path = out_dir / f"card_{art_id}_design_{d}.png"
                    self.generate_card(article, design=d, output_path=card_path, card_size=card_size)
                    generated.append(card_path)
            elif design_mode == "random":
                d = random.randint(0, len(DESIGN_NAMES) - 1)
                card_path = out_dir / f"card_{art_id}_design_{d}.png"
                self.generate_card(article, design=d, output_path=card_path, card_size=card_size)
                generated.append(card_path)
            elif design_mode == "cycle":
                d = idx % len(DESIGN_NAMES)
                card_path = out_dir / f"card_{art_id}_design_{d}.png"
                self.generate_card(article, design=d, output_path=card_path, card_size=card_size)
                generated.append(card_path)
            else:
                d = design_mode
                card_path = out_dir / f"card_{art_id}_design_{d}.png"
                self.generate_card(article, design=d, output_path=card_path, card_size=card_size)
                generated.append(card_path)

        log.info(f"Bulk generation finished! Total {len(generated)} cards saved to {out_dir}")
        return generated


def fetch_articles_from_api(limit=10, require_image=False):
    url = f"{API_BASE_URL}{NEWS_ENDPOINT}"
    fetch_count = max(limit * 2, 20) if require_image else limit
    log.info(f"Fetching latest articles from {url}")
    try:
        r = requests.get(url, params={"page_size": fetch_count}, timeout=15)
        r.raise_for_status()
        data = r.json()
        items = data.get("results") or (data if isinstance(data, list) else [])
        if require_image:
            items = [a for a in items if a.get("image") or a.get("featured_image")]
        return items[:limit]
    except Exception as e:
        log.error(f"Failed to fetch news from API: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Khobornama Bulk Photocard Generator")
    parser.add_argument("--count", type=int, default=5, help="Number of articles to process from API")
    parser.add_argument(
        "--design",
        default="split_10",
        help="Design mode: 'split_10' (first 10 in design 0, last 10 in design 1), 'cycle', 'random', '0' ('jamuna'), '1' ('somoy'), or 'all'",
    )
    parser.add_argument("--sample", action="store_true", help="Generate sample photocards for the 2 chosen designs")
    parser.add_argument("--outdir", default=str(OUTPUT_DIR), help="Output directory for generated photocards")
    args = parser.parse_args()

    generator = PhotocardGenerator()

    if args.sample:
        log.info("Generating sample photocards for the 2 chosen designs (Jamuna and Somoy)...")
        articles = fetch_articles_from_api(limit=1, require_image=True)
        if not articles:
            articles = [{
                "id": 999999,
                "title": "মিনারেলে ওয়াটারে বাড়তি কী এমন থাকে",
                "image": "https://media.channelionline.com/2026/11/Untitled15-7.jpg?w=1200",
                "published_at": "2026-11-25T13:16:51+06:00",
                "source": {
                    "name": "বাংলা ট্রিবিউন",
                    "logo": ""
                }
            }]
        article = articles[0]
        results = []
        for d in range(len(DESIGN_NAMES)):
            out_file = Path(args.outdir) / f"sample_design_{d+1}_{DESIGN_NAMES[d].replace(' ', '_').lower()}.png"
            generator.generate_card(article, design=d, output_path=out_file)
            results.append(out_file)
        print("\n=== Both Photocard Samples Generated Successfully! ===")
        for r in results:
            print(f" -> {r}")
        return

    articles = fetch_articles_from_api(limit=args.count)
    if not articles:
        log.error("No articles found to generate photocards.")
        sys.exit(1)

    design_mode = args.design
    if design_mode.isdigit():
        design_mode = int(design_mode)

    generator.generate_bulk(articles, output_dir=args.outdir, design_mode=design_mode)


if __name__ == "__main__":
    main()
