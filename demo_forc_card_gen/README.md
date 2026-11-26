# Khobornama Automated Photocard Generator (Python)

A high-performance Python port of the Flutter `ShareableNewsCard` widget, designed for automated bulk generation of social news photocards with pixel-perfect Bengali typography and authentic news layouts.

---

## 🎨 Supported Photocard Designs (Selected 2 Types)

| Index | Name | Style Inspiration | Description |
|---|---|---|---|
| **0** | **Jamuna TV Style** | Jamuna TV | Crimson card `#8B0000`, bold red title container (`#990000`), golden date, dark maroon brand footer (`#660000`) with dual branding |
| **1** | **Somoy News Style** | Somoy TV | Smooth top image gradient fade into pure white, centered vibrant red headline (`#E11B2D`), dual logos (Khobornama + Source) |

---

## 🚀 Quick Start & CLI Usage

### 1. Generate Samples for both Designs
Generates both Jamuna and Somoy styles for the latest news article from the API:
```bash
python demo_forc_card_gen/photocard_generator.py --sample
```
Outputs are saved in `demo_forc_card_gen/output/`.

### 2. Bulk Generation from Live API
Fetch latest articles and automatically alternate between both styles:
```bash
python demo_forc_card_gen/photocard_generator.py --count 10 --design cycle
```

### 3. Generate a Specific Design
Choose a specific style (by name or index `0` or `1`):
```bash
# Jamuna TV Style
python demo_forc_card_gen/photocard_generator.py --count 5 --design jamuna

# Somoy News Style
python demo_forc_card_gen/photocard_generator.py --count 5 --design somoy
```

### 4. Generate Both Variations for Every Article
```bash
python demo_forc_card_gen/photocard_generator.py --count 5 --design all
```

---

## 💻 Programmatic Usage in Python

```python
from demo_forc_card_gen.photocard_generator import PhotocardGenerator

generator = PhotocardGenerator()

article = {
    "id": 214871,
    "title": "অনিয়ম-দুর্নীতির অভিযোগে ঝিনাইদহের স্বাস্থ্য কর্মকর্তা ওএসডি",
    "image": "https://cdn.banglatribune.net/.../image.jpg",
    "published_at": "2026-11-25T13:16:51+06:00",
    "source": {
        "name": "বাংলা ট্রিবিউন",
        "logo": "https://api.khobornama.info.bd/media/media_logos/bangla-tribune.webp"
    }
}

# Generate single card (0: Jamuna, 1: Somoy)
generator.generate_card(article, design=0, output_path="output/jamuna_card.png")
generator.generate_card(article, design=1, output_path="output/somoy_card.png")

# Bulk generate
articles = [...]
generator.generate_bulk(articles, output_dir="output/", design_mode="cycle")
```
