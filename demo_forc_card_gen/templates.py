# HTML Templates for Khobornama Photocards
# Kept to the 2 chosen designs:
#  0: Jamuna TV Style (Bold Red Bottom Banner & Footer)
#  1: Somoy News Style (Gradient Fade + Red Key Headline + Dual Logos)

COMMON_HEAD = """
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;500;600;700&display=swap');
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}
html, body {
    width: 1080px;
    height: 1140px;
    margin: 0;
    padding: 0;
    overflow: hidden;
    background: transparent;
    font-family: 'Hind Siliguri', 'Nirmala UI', 'Kalpurush', sans-serif;
    -webkit-font-smoothing: antialiased;
}
.card-wrapper {
    width: 1080px;
    height: 1140px;
    overflow: hidden;
    position: relative;
    box-sizing: border-box;
    display: flex;
    flex-direction: column;
}
.source-badge {
    background: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 12px;
    padding: 6px 18px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
    height: 48px;
    max-width: 220px;
}
.source-badge img {
    max-height: 34px;
    max-width: 170px;
    object-fit: contain;
}
.source-badge span {
    font-size: 22px;
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
}
</style>
"""

def render_badge(source_name, source_logo_b64):
    if source_logo_b64:
        return f'<div class="source-badge"><img src="{source_logo_b64}" alt="{source_name}" /></div>'
    return f'<div class="source-badge"><span>{source_name}</span></div>'


def template_jamuna(title, date_str, image_b64, logo_b64, source_name, source_logo_b64):
    """
    Design 1: Jamuna TV Style
    - Deep crimson card background (#8B0000)
    - News photo on top (flexible, full width cover)
    - Red title container (#990000) with bold white Bengali title and golden date
    - Dark maroon footer bar (#660000) with Khobornama brand left and news source logo badge right
    """
    badge = render_badge(source_name, source_logo_b64)
    return f"""<!DOCTYPE html>
<html>
<head>
{COMMON_HEAD}
<style>
.card-wrapper {{
    background: #8B0000;
    border-radius: 40px;
    box-shadow: 0 16px 36px rgba(0,0,0,0.3);
}}
.img-box {{
    flex: 1 1 0;
    min-height: 0;
    position: relative;
    background: #1e1e1e;
    overflow: hidden;
}}
.img-box img {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
}}
.title-box {{
    background: #990000;
    padding: 24px 36px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}}
.title-text {{
    color: #ffffff;
    font-size: 40px;
    font-weight: 700;
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}}
.date-text {{
    color: #FFD700;
    font-size: 22px;
    font-weight: 600;
    margin-top: 10px;
}}
.footer-bar {{
    background: #660000;
    padding: 20px 36px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}
.brand-left {{
    display: flex;
    align-items: center;
    gap: 12px;
}}
.brand-left img {{
    width: 40px;
    height: 40px;
    border-radius: 8px;
}}
.brand-left .name {{
    color: #ffffff;
    font-size: 28px;
    font-weight: 700;
}}
.brand-left .domain {{
    color: #FFD700;
    font-size: 24px;
    font-weight: 600;
}}
</style>
</head>
<body>
<div class="card-wrapper">
    <div class="img-box">
        <img src="{image_b64}" />
    </div>
    <div class="title-box">
        <div class="title-text">{title}</div>
        <div class="date-text">প্রকাশিত: {date_str}</div>
    </div>
    <div class="footer-bar">
        <div class="brand-left">
            <img src="{logo_b64}" />
            <span class="name">খবরনামা</span>
            <span class="domain">• khobornama.info.bd</span>
        </div>
        {badge}
    </div>
</div>
</body>
</html>"""


def template_somoy(title, date_str, image_b64, logo_b64, source_name, source_logo_b64):
    """
    Design 2: Somoy News Style
    - Pure white card (#ffffff) with subtle border and rounded corners
    - News photo on top with seamless vertical gradient fade into white background
    - Bold vibrant red Bengali headline (#E11B2D)
    - Centered row of dual logos: Khobornama icon + name, alongside the source logo badge
    - Subtitle footer: date • khobornama.info.bd in slate (#64748B)
    """
    badge = render_badge(source_name, source_logo_b64)
    return f"""<!DOCTYPE html>
<html>
<head>
{COMMON_HEAD}
<style>
.card-wrapper {{
    background: #ffffff;
    border-radius: 40px;
    border: 2px solid #e2e8f0;
    box-shadow: 0 16px 36px rgba(0,0,0,0.12);
}}
.img-box {{
    flex: 1 1 0;
    min-height: 0;
    position: relative;
    background: #f1f5f9;
    overflow: hidden;
}}
.img-box img {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
}}
.gradient-overlay {{
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom, 
        transparent 35%, 
        rgba(255, 255, 255, 0.45) 65%, 
        #ffffff 94%, 
        #ffffff 100%
    );
}}
.content-box {{
    padding: 12px 40px 32px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    background: #ffffff;
}}
.title-text {{
    color: #E11B2D;
    font-size: 44px;
    font-weight: 700;
    line-height: 1.35;
    margin-bottom: 20px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}}
.logos-row {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 24px;
    margin-bottom: 14px;
}}
.brand-group {{
    display: flex;
    align-items: center;
    gap: 10px;
}}
.brand-group img {{
    width: 40px;
    height: 40px;
    border-radius: 8px;
}}
.brand-group span {{
    font-size: 28px;
    font-weight: 700;
    color: #0F172A;
}}
.footer-date {{
    font-size: 24px;
    color: #64748B;
    font-weight: 600;
}}
</style>
</head>
<body>
<div class="card-wrapper">
    <div class="img-box">
        <img src="{image_b64}" />
        <div class="gradient-overlay"></div>
    </div>
    <div class="content-box">
        <div class="title-text">{title}</div>
        <div class="logos-row">
            <div class="brand-group">
                <img src="{logo_b64}" />
                <span>খবরনামা</span>
            </div>
            {badge}
        </div>
        <div class="footer-date">{date_str}  •  khobornama.info.bd</div>
    </div>
</div>
</body>
</html>"""


DESIGN_TEMPLATES = {
    0: template_jamuna,
    1: template_somoy,
    "jamuna": template_jamuna,
    "somoy": template_somoy,
}

DESIGN_NAMES = [
    "Jamuna TV Style",
    "Somoy News Style",
]
