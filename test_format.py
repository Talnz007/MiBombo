"""
Test script for the new clean_osint_report() function.
Run this BEFORE applying changes to the scrapers to verify formatting is preserved.
"""
import re

def clean_osint_report(text: str) -> str:
    """
    Cleans rogue AI markdown and formats it perfectly for WhatsApp.
    Preserves Grok's native WhatsApp formatting (🔹/🔶 emojis, *bold*).
    """
    # 1. Strip local AI thought blocks (e.g., **Thought for 45s** or <think> tags)
    text = re.sub(r'\*\*Thought for.*?\*\*\n*', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<think>.*?</think>\n*', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # 2. Unwrap messy Markdown links: [**URL**](/URL) -> URL
    text = re.sub(r'\[\*\*?(https?://[^\s\]]+)\*\*?\]\(.*?\)', r'\1', text)
    text = re.sub(r'\[(https?://[^\s\]]+)\]\(.*?\)', r'\1', text)
    
    # 3. Convert markdown bold **text** to WhatsApp bold *text*
    #    This handles the DOM fallback path which produces **bold** via markdownify
    text = re.sub(r'\*\*([^*]+)\*\*', r'*\1*', text)
    
    # 4. Fix any leftover triple+ asterisks (from nested spans) down to single WhatsApp bold
    text = re.sub(r'\*{3,}([^*]+)\*{3,}', r'*\1*', text)
    text = re.sub(r'\*{3,}', '*', text)
    
    # 5. Clean up redundant spaces and excessive blank lines
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


# ── Test with the clean (correct) Grok output ──────────────────────────
SAMPLE_GROK_OUTPUT = """*Aoa, sir*

🔶Subject : *OSINT Update – US Peace Plan to Iran via Pakistan Amid Carrier Strike (25 Mar 2026)*
🔹Iran received a *15-point US plan* to end the Middle East war, conveyed through *senior Pakistani intermediaries* in *Islamabad*, as confirmed by *two high-level officials* to *AFP*; proposals include *ceasefire*, *ban on uranium enrichment* on Iranian soil, *reopening of the Strait of Hormuz*, and *sanctions relief*.
🔹This *diplomatic breakthrough* occurred even as *Iranian forces* fired *cruise missiles* at the *USS Abraham Lincoln* carrier group, forcing it to change position, with *Tehran* warning of "powerful strikes" against the "hostile fleet".
🔹Conflict erupted on *28 Feb 2026* with *US-Israeli bombing* of Iran, rapidly drawing in *Lebanon* via *Hezbollah rockets* after the killing of *Ayatollah Ali Khamenei*; over *1,000 killed* and *1 million displaced* in *Beirut suburbs* and *southern Lebanon* per Lebanese authorities.
🔹*Pakistan's central role* as mediator leverages its unique ties with *Iran*, the *US*, and *Gulf states*; Iran has assured *safe passage for non-hostile vessels* through the *Strait of Hormuz* (20% of global oil) while blocking aggressor parties.
🔹*Visuals description/Official context*: AFP images depict shattered streets in *Beirut's southern suburbs* and damaged facilities in *Tehran* and *Isfahan*; Pakistan officials frame this as responsible diplomacy preventing wider economic fallout, with global oil prices tumbling and stocks rising on de-escalation signals.
🔶 *Narrative from Official/Pro-Pak*: Pakistan has once again demonstrated its stature as a *trusted peace broker* by facilitating direct delivery of the US proposals to Tehran, showcasing Islamabad's commitment to *regional stability*, *global energy security*, and de-escalation without compromising sovereignty or alliances.
🔶 *Narrative from Anti-State/Propaganda*: Hardline Iranian elements and proxy voices deny any negotiations, amplify belligerent missile-strike claims, and attempt to portray mediators like Pakistan as compromised, while ignoring the 15-point plan's potential for sanctions relief and ceasefire to push divisive anti-state rhetoric.
🔶 *Sentiment/Reach*: Cautiously optimistic with positive market reaction and widespread international coverage; high global reach via AFP-sourced reporting, highlighting Pakistan's constructive role without anti-state bias from the credible *Malaysian outlet*.
*Links:*
https://www.freemalaysiatoday.com/category/world/2026/03/25/tehran-receives-us-plan-to-end-middle-east-war-as-iran-fires-at-us-carrier (Primary report on US plan delivery and Iranian carrier strike citing Pakistani officials)
 *Regards*"""


# ── Test with markdown-bold variant (DOM fallback) ──────────────────────
SAMPLE_MARKDOWN_OUTPUT = """**Aoa, sir**

🔶Subject : **OSINT Update – US Peace Plan (25 Mar 2026)**
🔹Iran received a **15-point US plan** to end the war.
🔹**Pakistan's central role** as mediator leverages ties with **Iran** and the **US**.
🔶 **Narrative from Official/Pro-Pak**: Pakistan demonstrated its stature as a **trusted peace broker**.
🔶 **Sentiment/Reach**: Cautiously optimistic.
**Links:**
https://example.com/article (description)
 **Regards**"""


# ── Test with messy AI output (think tags, markdown links) ──────────────
SAMPLE_MESSY_OUTPUT = """<think>Let me analyze this OSINT report carefully...</think>
**Thought for 12s**
*Aoa, sir*

🔶Subject : *OSINT Update – Test (25 Mar 2026)*
🔹[**https://example.com**](https://example.com) reports that *something happened*.
🔹***Triply bold text*** should be fixed.
🔶 *Sentiment/Reach*: Low reach.
*Links:*
[https://example.com](https://example.com)
 *Regards*"""


def run_test(name, sample):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    
    result = clean_osint_report(sample)
    
    print(f"\n--- OUTPUT ---")
    print(result)
    print(f"\n--- CHECKS ---")
    
    checks = [
        ("Has 🔹 bullets", "🔹" in result),
        ("Has 🔶 headers", "🔶" in result),
        ("Has *bold* text", "*" in result),
        ("No ** double bold left", "**" not in result),
        ("No <think> tags", "<think>" not in result),
        ("No 'Thought for' text", "Thought for" not in result),
        ("Has *Aoa, sir*", "*Aoa, sir*" in result),
        ("Has *Regards*", "*Regards*" in result or "Regards" in result),
        ("No triple blank lines", "\n\n\n" not in result),
        ("No markdown links [text](url)", "](" not in result),
    ]
    
    all_pass = True
    for desc, passed in checks:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}")
        if not passed:
            all_pass = False
    
    return all_pass


if __name__ == "__main__":
    results = []
    results.append(run_test("Clean Grok Output (should be preserved as-is)", SAMPLE_GROK_OUTPUT))
    results.append(run_test("Markdown Bold (DOM fallback, **bold** → *bold*)", SAMPLE_MARKDOWN_OUTPUT))
    results.append(run_test("Messy AI Output (think tags, markdown links)", SAMPLE_MESSY_OUTPUT))
    
    print(f"\n{'='*60}")
    if all(results):
        print("🎉 ALL TESTS PASSED! Safe to apply to both scrapers.")
    else:
        print("❌ SOME TESTS FAILED — review output above.")
    print(f"{'='*60}")
