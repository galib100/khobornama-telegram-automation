import os
import sys
import shutil
import base64
import json
import logging
from pathlib import Path
import subprocess
import requests
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CardGen")

def get_browser_path():
    env_browser = os.getenv("CHROME_PATH") or os.getenv("BROWSER_PATH")
    if env_browser and os.path.exists(env_browser):
        return env_browser

    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge", "chrome"):
        p = shutil.which(name)
        if p and os.path.exists(p):
            return p

    candidates = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Linux
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
        # Windows
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def image_to_base64(url_or_path, timeout=10):
    if not url_or_path:
        return ""
    try:
        if str(url_or_path).startswith(("http://", "https://")):
            r = requests.get(url_or_path, timeout=timeout)
            if r.status_code == 200:
                ct = r.headers.get("content-type", "image/jpeg")
                b64 = base64.b64encode(r.content).decode("utf-8")
                return f"data:{ct};base64,{b64}"
        else:
            path = Path(url_or_path)
            if path.exists():
                ext = path.suffix.lower().lstrip(".")
                mime = "image/png" if ext == "png" else ("image/jpeg" if ext in ("jpg", "jpeg") else "image/webp")
                b64 = base64.b64encode(path.read_bytes()).decode("utf-8")
                return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.warning(f"Failed to fetch image {url_or_path}: {e}")
    return ""

def render_html_to_image(html_str, output_path, width=1080, height=1140):
    browser = get_browser_path()
    if not browser:
        raise RuntimeError("Neither Microsoft Edge nor Google Chrome found for headless rendering.")
    
    tmp_html = output_path.with_suffix(".tmp.html")
    tmp_html.write_text(html_str, encoding="utf-8")
    
    # On Windows, headless Chromium window-size includes ~24px width and ~93px height
    # of non-client window frame. On Linux/macOS, window-size matches viewport directly.
    if sys.platform == "win32":
        win_w = width + 24
        win_h = height + 93
    else:
        win_w = width
        win_h = height
    
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--hide-scrollbars",
        f"--window-size={win_w},{win_h}",
        f"--screenshot={output_path.resolve()}",
        f"{tmp_html.resolve()}"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if tmp_html.exists():
        tmp_html.unlink()
        
    if res.returncode != 0 or not output_path.exists():
        raise RuntimeError(f"Rendering failed (code {res.returncode}): {res.stderr}")
    
    # Crop to exact viewport dimensions (removes any frame bleed)
    with Image.open(output_path) as im:
        if im.size != (width, height):
            cropped = im.crop((0, 0, width, height))
            cropped.save(output_path)
            
    return output_path
