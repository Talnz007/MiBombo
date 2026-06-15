import os
import json
import re
import requests
from datetime import datetime, timezone, timedelta

from grok_reporter import query_grok

OLLAMA_URL = "http://localhost:11434/api/generate"
# Mixed-model approach to bypass safety filters on text
OLLAMA_TEXT_MODEL = "dolphin-llama3"  # Uncensored text model for OSINT analysis
OLLAMA_VL_MODEL = "qwen3-vl:4b"  # Vision model for image analysis

PROMPT_TEMPLATE = """You are a South Asia OSINT analyst specializing in militant activity (Pakistan/Afghanistan/India).
[TERMINOLOGY: TTA/Afghan Taliban = FAK (Fitna al-Khawarij), Fighters = Ks (Khawarij), FAH Fighters = Ts (Terrorists). Use these terms.]

Output EXACTLY one tag on the first line:
[CATEGORY: 1] -> GLOBAL (NOT internal Pak/Afg: Iran, Israel, US, International diplomacy, etc.)
[CATEGORY: 2] -> REGIONAL (ONLY Internal Pak/Afg: domestic politics, army ops, TTP/BLA/ISKP attacks, border clashes.)

Output EXACTLY one priority tag on the SECOND line (immediately after the CATEGORY tag):
[PRIORITY: 1] -> CRITICAL (active/imminent attack, mass casualty event, breaking military operation, hostage situation, or assassination — something that demands immediate attention within minutes)
[PRIORITY: 2] -> IMPORTANT (confirmed attack aftermath, significant political development, major troop movement, verified propaganda campaign, or diplomatic crisis — urgent but not time-critical to the minute)
[PRIORITY: 3] -> ROUTINE (background analysis, historical context, low-engagement social media chatter, scheduled press statement, or general situational awareness — can wait hours)

Rules for priority tagging:
- Always output the tag in exactly this format: [PRIORITY: N] where N is 1, 2, or 3.
- Place it on its own line, immediately after the [CATEGORY: N] tag and before "*Aoa, sir*".
- When in doubt, prefer PRIORITY 2 over PRIORITY 1 to avoid alarm fatigue.
- NEVER omit the tag — every report must include exactly one.

Format:
*Aoa, sir*
🔶Subject : *OSINT Update – [Short Title] ([Date])*
🔹[Concise facts, bold key names/numbers/locations]
🔹[Next fact, bold critical items]
🔹[Visuals description/Official context]
🔶 *Narrative from Official/Pro-Pak*: [1-2 sentences]
🔶 *Narrative from Anti-State/Propaganda*: [1-2 sentences]
🔶 *Sentiment/Reach*: [Sentiment & SM metrics]
Links:
- https://x.com/... (description)
- [Max 10 primary links]
 *Regards*

Rules:
- 250–450 words.
- Bold ONLY important names, numbers, locations, or key phrases.
- Use 🔹 for bullets, 🔶 for headers.
- Filter out anti-Pakistan bias/propaganda and frame the report from a pro-Pakistan/pro-State perspective.
- Critically evaluate the source account's credibility (e.g., identify pro-TTP, pro-BLA, or pro-Afghan propaganda) and counter anti-state narratives while highlighting the official state/ISPR perspective.
- End with " *Regards*".
- NO intros/outros or AI images.
- Convert raw input/links immediately. Just wait for my input."""

# ──────────────────── Relevance Filter ────────────────────

RELEVANCE_KEYWORDS = [
    # Countries & broad regions
    "pakistan", "افغانستان", "afghanistan", "afghan", "india", "iran", "پاکستان", "بھارت", "ایران",
    "balochistan", "waziristan", "fata", "kpk", "khyber", "بلوچستان", "وزیرستان", "فاٹا", "خیبر",
    "sindh", "punjab", "gilgit", "kashmir", "loc", "durand", "سندھ", "پنجاب", "گلگت", "کشمیر",
    
    # Specific Cities / Districts / Hotspots
    "kabul", "kandahar", "paktia", "paktika", "ghazni", "helmand", "nangarhar", "kunar", "khost", "nuristan", "کابل", "قندھار",
    "torkham", "chaman", "spin boldak", "angoor adda", "ghulam khan", "طورخم", "چمن",
    "tirah", "kurram", "parachinar", "bannu", "lakki marwat", "di khan", "dera ismail", "tank", "mir ali", "miranshah", "razmak", "تیراہ", "پاراچنار", "بنوں", "میرانشاہ",
    "gwadar", "mach", "panjgur", "turbat", "kech", "awaran", "khuzdar", "harnai", "zhob", "quetta", "گوادر", "مچھ", "تربت", "خضدار", "کوئٹہ",
    "peshawar", "swat", "bajaur", "mohmand", "orokzai", "chitral", "dir", "پشاور", "سوات", "باجوڑ", "چترال",
    
    # Organisations & factions
    "ttp", "bla", "blf", "iskp", "isil", "isis", "daesh", "ispp", "داعش", "ٹی ٹی پی", "بی ایل اے",
    "taliban", "talibs", "tta", "nrf", "tipl", "tlp", "etim", "bra", "uba", "bna", "brm", "طالبان", "تحریک لبیک",
    "al qaeda", "alqaeda", "aqis", "muttaqi", "sirajuddin", "haqqani", "mehsud", "bugti", "marri", "القاعدہ", "حقانی", "محسود",
    "ispr", "dgispr", "pak army", "pakistan army", "afghan forces", "gdi", "پاک فوج", "آئی ایس پی آر",
    "coas", "rawalpindi", "ghq", "isi", "mi", "ib", "راولپنڈی", "جی ایچ کیو",
    "fak", "khawarij", "fitna", "sarmachar", "خوارج", "فتنۃ", "سرمچار",
    
    # Military, LEA, and Kinetic terms
    "terrorist", "terrorism", "militant", "insurgent", "rebel", "separatist", "دہشتگرد", "دہشت گرد", "عسکریت پسند", "باغی",
    "airstrike", "drone", "operation", "convoy", "ibo", "intelligence based", "فضائی حملہ", "ڈرون", "آپریشن",
    "fc ", "frontier corps", "ctd", "counter terrorism", "police", "levies", "checkpost", "camp", "cantt", "پولیس", "چیک پوسٹ",
    "martyr", "shaheed", "idf", "cross-border", "shelling", "firing", "clash", "ambush", "شہید", "فائرنگ", "جھڑپ", "حملہ",
    "counterterror", "intel", "osint", "threat", "security", "سیکورٹی", "انٹیلیجنس",
    "ied", "suicide", "blast", "attack", "explosion", "vbied", "دھماکہ", "خودکش", "حملہ",
    "deployment", "troop", "military", "helicopter", "gunship", "ssg", "فوجی", "ہیلی کاپٹر",
    
    # Militant / local slang
    "fidayeen", "istishhadi", "ghazi", "mujahideen", "kuffar", "murtad", "apostate", "فدائین", "استشھادی", "غازی", "مجاہدین", "کفار", "مرتد",
    
    # Political & Geopolitical
    "pti", "pmln", "ppp", "jui",
    "imran khan", "nawaz", "bilawal", "fazlur rehman", "khan", "عمران خان", "نواز", "فضل الرحمان", "بلاول",
    "bajwa", "munir", "asim", "قاضی فائز", "باجوہ", "عاصم منیر",
    "israel", "tel aviv", "gaza", "palestine", "zionist", "usa", "america", "cia", "mossad", "اسرائیل", "تل ابیب", "قادیان", "تہران", "فلسطین", "امریکہ"
]

def is_relevant_post(item: dict) -> bool:
    """Check if a post is relevant to Pakistan/Afghanistan/India/terrorism OSINT."""
    text = (item.get("text", "") + " " + item.get("account", "")).lower()
    for kw in RELEVANCE_KEYWORDS:
        if kw in text:
            return True
    return False


# ──────────────────── Category Parser ────────────────────

import re as _re
# No ^ anchor — Grok sometimes emits whitespace/BOM before the tag;
# a plain search anywhere in the response is more robust.
_CATEGORY_RE = _re.compile(r'\[CATEGORY:\s*([123])\]', _re.IGNORECASE)

def parse_category(report: str) -> tuple:
    """
    Extract the [CATEGORY: N] tag from Grok's response.
    Returns (category_int, cleaned_report):
        1 = global   -> 'Automated news'
        2 = regional -> 'Regional news'
        3 = other    -> 'Other news'
    Defaults to 1 if tag missing.
    """
    m = _CATEGORY_RE.search(report)
    if m:
        cat = int(m.group(1))
        if cat not in (1, 2, 3):
            cat = 1  # anything unexpected defaults to global
        cleaned = _CATEGORY_RE.sub('', report).strip()
        print(f"[+] parse_category: found [CATEGORY: {cat}] in response.")
        return cat, cleaned
    print("[!] No [CATEGORY] tag found in Grok response. Defaulting to category 1.")
    return 1, _CATEGORY_RE.sub('', report).strip()

# ──────────────────── Ollama API ────────────────────

def _query_ollama(prompt: str, temperature: float = 0.4, image_path: str = None, system_prompt: str = None) -> str:
    """Send a prompt to Ollama and return the response text. Supports images for VL models."""
    import base64
    try:
        # Pick the correct model: Use the VL model ONLY if we have a valid image.
        has_image = image_path and os.path.exists(image_path) and not image_path.endswith("blank_msg.png")
        model_to_use = OLLAMA_VL_MODEL if has_image else OLLAMA_TEXT_MODEL
        
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
            }
        }
        
        if system_prompt:
            if model_to_use == OLLAMA_VL_MODEL:
                # Vision models often struggle with separate system prompts, so prepend it
                payload["prompt"] = f"{system_prompt}\n\n{prompt}"
            else:
                payload["system"] = system_prompt
            
        print(f"[DEBUG] Prompt length: {len(prompt)}")
        print(f"[*] Using model: {model_to_use}")
        
        # If we have a screenshot, encode it as base64 for the VL model
        if has_image:
            with open(image_path, "rb") as f:
                b64_img = base64.b64encode(f.read()).decode("utf-8")
            payload["images"] = [b64_img]
            print(f"[*] Including screenshot for visual analysis: {os.path.basename(image_path)}")

        resp = requests.post(OLLAMA_URL, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        raw = data.get("response", "").strip()
        print(f"[DEBUG] {model_to_use} raw BEFORE stripping: {repr(raw)}")
        
        # Only try to strip <think> tags if this is actually a thinking model
        if "<think>" in raw:
            raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            
        print(f"[DEBUG] {model_to_use} raw output length: {len(raw)}\n[DEBUG] {model_to_use} raw output:\n{raw}")
        return raw
    except Exception as e:
        print("\n\n[-] ======================================")
        print(f"[-] Ollama query failed: {str(e)}")
        print("[-] ======================================\n\n")
        return ""

# ──────────────────── Date Formatting ────────────────────

def _format_human_date(date_str: str) -> str:
    """Convert ISO timestamp to readable date like 'February 24, 2026'"""
    try:
        clean = date_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        pkt = dt.astimezone(timezone(timedelta(hours=5)))
        return pkt.strftime("%B %d, %Y")
    except Exception:
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", ""))
            return dt.strftime("%B %d, %Y")
        except Exception:
            return date_str

# ──────────────────── Translation ────────────────────

def _translate_if_needed(text: str) -> str:
    """Translate non-English text (Arabic, Pashto, Urdu, Hebrew, etc.) to English."""
    import re
    # Count basic English alphabet characters
    alpha_chars = len(re.findall(r'[a-zA-Z]', text))
    
    # Count foreign letters (any alphabetic character outside basic ASCII)
    foreign_letters = sum(1 for c in text if c.isalpha() and ord(c) > 127)
    
    if foreign_letters < 5 or (alpha_chars > foreign_letters * 2):
        return text
    
    try:
        print(f"[DEBUG] Alpha chars: {alpha_chars}, Foreign chars: {foreign_letters}")
        from deep_translator import GoogleTranslator
        # GoogleTranslator auto-detects source language
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        print(f"[DEBUG] GoogleTranslator returned: {repr(translated)}")
        if translated and translated.strip() != text.strip():
            return f'{translated}\n\n[Original]: "{text}"'
    except Exception as e:
        print(f"[!] Translation failed: {e}")
    
    return text

# ──────────────────── Report Generation ────────────────────

def enforce_message_format(report_text: str) -> str:
    """Ensure *Aoa, sir* is the very first line. Move any stray links/categories below."""
    lines = report_text.splitlines()
    aoa_index = -1
    for i, line in enumerate(lines):
        if "aoa, sir" in line.lower():
            aoa_index = i
            break
            
    if aoa_index > 0:
        pretext = lines[:aoa_index]
        pretext = [p for p in pretext if p.strip()]
        main_report = lines[aoa_index:]
        
        regards_index = -1
        for i in range(len(main_report) - 1, -1, -1):
            if "regards" in main_report[i].lower() or "links:" in main_report[i].lower():
                regards_index = i
                break
                
        if regards_index != -1:
            for p in reversed(pretext):
                main_report.insert(regards_index, p)
        else:
            main_report.extend(pretext)
            
        return "\n".join(main_report)
        
    return report_text

def generate_osint_report(item: dict, img_path: str = None) -> str:
    """
    Generate a detailed OSINT report via Grok, or use a fallback format.
    """
    platform_name = item.get("platform", "").capitalize()
    source_name = item.get("account", item.get("channel", item.get("site", "Unknown")))
    url = item.get("url", "No URL")
    raw_date = item.get("date", "Unknown Date")
    human_date = _format_human_date(raw_date)
    post_text = item.get("text", "No text provided.")
    
    # Translate if needed
    caption = post_text
    caption = _translate_if_needed(caption)

    # Engagement metrics
    metrics = item.get("metrics", {})
    metrics_parts = []
    if metrics.get("views"): metrics_parts.append(f"{metrics['views']} views")
    if metrics.get("likes"): metrics_parts.append(f"{metrics['likes']} likes")
    if metrics.get("reposts"): metrics_parts.append(f"{metrics['reposts']} reposts")
    if metrics.get("replies"): metrics_parts.append(f"{metrics['replies']} replies")
    metrics_str = ", ".join(metrics_parts) if metrics_parts else "Engagement data being tracked"

    print(f"[*] Formatting prompt for Grok (@{source_name})...")
    
    # Construct the one-shot prompt for Grok
    grok_prompt = f"""{PROMPT_TEMPLATE}

attack link here : {url}

[END OF INPUT]
"""
    
    # Query Grok
    report = query_grok(grok_prompt, timeout_seconds=420)
    
    if not report or len(report) < 100:
        print("[-] Grok failed to generate a valid report. Falling back to local uncensored model...")
        local_prompt = f"{PROMPT_TEMPLATE}\n\nHere is the raw text to analyze:\nPlatform: {platform_name}\nAccount: {source_name}\nLinks: {url}\n\n{caption}"
        report = _query_ollama(local_prompt, temperature=0.4)
        
    if not report or len(report) < 100:
        print("[-] Local AI failed as well. Using raw fallback format.")
        # Build the fallback report
        report = f"""*Aoa, sir*

\U0001F536 *Subject : RAW OSINT Update – {human_date}*
Platform: {platform_name} | Account: @{source_name}
Metrics: {metrics_str}

\U0001F539 *Raw Post Text & OCR*: 
{caption}

Links:
- {url}

--------------------------------------------------
[PROMPT TEMPLATE FOR GROK/GEMINI]

{PROMPT_TEMPLATE}
"""

    return report


if __name__ == "__main__":
    pass
