import re
import random
import time
from django.conf import settings
from difflib import SequenceMatcher

BETIKA_BASE = "https://www.betika.com"

# Sports + their Betika URLs + which markets to dig into
SPORT_CONFIG = {
    "football": {
        "urls": [
            f"{BETIKA_BASE}/en-ke/s/football/highlights",
            f"{BETIKA_BASE}/en-ke/s/football/epl",
            f"{BETIKA_BASE}/en-ke/s/football/ucl",
            f"{BETIKA_BASE}/en-ke/s/football/laliga",
            f"{BETIKA_BASE}/en-ke/s/football/bundesliga",
            f"{BETIKA_BASE}/en-ke/s/football/serie-a",
        ],
        "market_type": "3way",
    },
    "tennis": {
        "urls": [
            f"{BETIKA_BASE}/en-ke/s/tennis/highlights",
            f"{BETIKA_BASE}/en-ke/s/tennis/atp",
            f"{BETIKA_BASE}/en-ke/s/tennis/wta",
        ],
        "market_type": "2way",
    },
    "basketball": {
        "urls": [
            f"{BETIKA_BASE}/en-ke/s/basketball/highlights",
            f"{BETIKA_BASE}/en-ke/s/basketball/nba",
            f"{BETIKA_BASE}/en-ke/s/basketball/euroleague",
        ],
        "market_type": "2way",
    },
    "cricket": {
        "urls": [f"{BETIKA_BASE}/en-ke/s/cricket/highlights"],
        "market_type": "2way",
    },
    "rugby": {
        "urls": [f"{BETIKA_BASE}/en-ke/s/rugby/highlights"],
        "market_type": "2way",
    },
    "american_football": {
        "urls": [f"{BETIKA_BASE}/en-ke/s/american-football/highlights"],
        "market_type": "2way",
    },
    "ice_hockey": {
        "urls": [f"{BETIKA_BASE}/en-ke/s/ice-hockey/highlights"],
        "market_type": "3way",
    },
    "volleyball": {
        "urls": [f"{BETIKA_BASE}/en-ke/s/volleyball/highlights"],
        "market_type": "2way",
    },
}


def normalise(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"\b(fc|af|sc|cf|ac|bc|bk|fk|sk|if|afc|ufc|rcd|cd|ud|sd|ca|ce)\b", "", name)
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def is_team_name(text: str) -> bool:
    text = text.strip()
    if not text or len(text) < 2 or len(text) > 60:
        return False
    if chr(8226) in text or "" in text:
        return False
    if re.match(r"^\d+[\.:]\d+", text):   # time like "19:00"
        return False
    if any(kw in text.lower() for kw in [
        "league", "cup", "division", "international", "friendly",
        "nations", "world cup", "euro", "africa", "fifa", "afc",
        "nba", "nhl", "khl", "bbl", "highlights", "today", "tomorrow",
        "live", "odds", "bet", "more", "show", "view"
    ]):
        return False
    return True


def fuzzy_match(name: str, db_names: list, threshold: float = 0.58):
    nb = normalise(name)
    best, best_score = None, 0.0
    for db_name in db_names:
        score = SequenceMatcher(None, nb, normalise(db_name)).ratio()
        if score > best_score:
            best, best_score = db_name, score
    return best if best_score >= threshold else None


#  Human behaviour helpers 

def human_delay(min_ms=400, max_ms=1400):
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def human_scroll(page, steps=5):
    for _ in range(steps):
        dist = random.randint(200, 600)
        page.evaluate(f"window.scrollBy(0, {dist})")
        human_delay(300, 900)
    # Occasionally scroll back up a bit (like a human re-reading)
    if random.random() < 0.3:
        page.evaluate(f"window.scrollBy(0, -{random.randint(100,300)})")
        human_delay(200, 500)


def human_mouse_wiggle(page):
    x = random.randint(100, 900)
    y = random.randint(100, 500)
    page.mouse.move(x, y)
    human_delay(100, 300)


def dismiss_popups(page):
    for sel in [
        "button:has-text('Accept')", "button:has-text('Close')",
        "button:has-text('Got it')", "button:has-text('OK')",
        "[aria-label='Close']", "[class*='close-btn']",
        "[class*='modal'] button", "[class*='popup'] button",
        "[class*='cookie'] button",
    ]:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=1000):
                btn.click()
                human_delay(300, 700)
        except Exception:
            pass


#  Main scraper class 

class BetikaOdds:

    def __init__(self, headless=None):
        self.headless = headless if headless is not None else getattr(settings, "BETIKA_HEADLESS", True)
        self.results  = {}

    def scrape(self, sports: list = None, max_per_url: int = 60,
               deep: bool = True) -> dict:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

        if not sports:
            sports = ["football", "tennis", "basketball"]

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=self.headless,
                slow_mo=50,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ]
            )
            ctx = browser.new_context(
                viewport={"width": 1366, "height": 768},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-KE",
                timezone_id="Africa/Nairobi",
            )
            # Mask webdriver fingerprint
            ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-KE','en']});
            """)
            page = ctx.new_page()
            page.set_default_timeout(30000)

            try:
                for sport in sports:
                    cfg = SPORT_CONFIG.get(sport)
                    if not cfg:
                        print(f"[Betika] Unknown sport: {sport}")
                        continue
                    for url in cfg["urls"]:
                        print(f"\n[Betika] {sport.upper()}  {url}")
                        human_delay(800, 2000)
                        self._scrape_listing(
                            page, url, sport,
                            cfg["market_type"],
                            max_per_url, deep
                        )
            except PWTimeout as e:
                print(f"[Betika] Timeout: {e}")
                page.screenshot(path="betika_timeout.png")
            except Exception as e:
                print(f"[Betika] Error: {e}")
                import traceback; traceback.print_exc()
                try:
                    page.screenshot(path="betika_error.png")
                except Exception:
                    pass
            finally:
                browser.close()

        return self.results

    #  Listing page (e.g. /epl) 

    def _scrape_listing(self, page, url, sport, market_type,
                         max_per_url, deep):
        from playwright.sync_api import TimeoutError as PWTimeout
        page.goto(url, wait_until="domcontentloaded")
        human_delay(2000, 3500)
        dismiss_popups(page)
        human_mouse_wiggle(page)
        human_scroll(page, steps=random.randint(4, 8))

        # Find match rows
        match_rows = []
        for sel in [".prebet-match", ".slip-row", "[class*='match-row']",
                    "[class*='event-row']", "[class*='prebet']",
                    "[class*='match_row']"]:
            rows = page.locator(sel).all()
            if len(rows) > 2:
                print(f"[Betika] Selector '{sel}'  {len(rows)} rows")
                match_rows = rows[:max_per_url]
                break

        if not match_rows:
            print("[Betika] No rows found  saving debug files.")
            with open(f"betika_{sport}_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            page.screenshot(path=f"betika_{sport}_page.png", full_page=True)
            print(f"[Betika] Saved betika_{sport}_page.html")
            return

        scraped = 0
        for i, row in enumerate(match_rows):
            try:
                if deep:
                    result = self._scrape_match_deep(page, row, sport, market_type, i)
                else:
                    result = self._extract_from_row(row, market_type)

                if result:
                    key = f"{result['home']} vs {result['away']}"
                    self.results[key] = result
                    scraped += 1
                    print(f"  [{sport}] {key} | markets: {list(result['markets'].keys())}")

                # Human-like pacing  occasional longer pauses
                if i % 5 == 0 and i > 0:
                    human_delay(1000, 2500)
                else:
                    human_delay(200, 600)

            except Exception as e:
                continue

        print(f"[Betika] {scraped}/{len(match_rows)} matches scraped for {sport}")

    #  Deep scrape: click into match, get all markets 

    def _scrape_match_deep(self, page, row, sport, market_type, index):
        from playwright.sync_api import TimeoutError as PWTimeout

        # First extract basic info from the listing row
        base = self._extract_from_row(row, market_type)
        if not base:
            return None

        # Try to find and click the match link
        try:
            link = row.locator("a[href*='/match/'], a[href*='/event/'], "
                               "a[href*='/fixture/'], [class*='match-link']").first
            href = link.get_attribute("href")
            if not href:
                return base  # Fall back to listing data

            match_url = href if href.startswith("http") else f"{BETIKA_BASE}{href}"
            human_delay(300, 800)
            human_mouse_wiggle(page)

            # Open in same tab
            page.goto(match_url, wait_until="domcontentloaded")
            human_delay(1500, 3000)
            dismiss_popups(page)
            human_scroll(page, steps=3)

            # Scrape all market sections
            all_markets = self._extract_all_markets_from_match_page(page, market_type)
            if all_markets:
                base["markets"].update(all_markets)

            # Go back
            page.go_back(wait_until="domcontentloaded")
            human_delay(1000, 2000)

        except (PWTimeout, Exception):
            pass   # Return whatever we got from listing

        return base

    def _extract_all_markets_from_match_page(self, page, market_type) -> dict:
        """Scrape every market accordion on a match detail page."""
        markets = {}
        human_delay(500, 1000)

        # Expand all market sections
        expand_btns = page.locator(
            "[class*='market-header'], [class*='accordion'], "
            "[class*='expand'], [class*='collapse']"
        ).all()
        for btn in expand_btns[:20]:
            try:
                if btn.is_visible(timeout=500):
                    btn.click()
                    human_delay(150, 400)
            except Exception:
                pass

        # Scrape market sections
        market_sections = page.locator(
            "[class*='market-group'], [class*='market-section'], "
            "[class*='market-container'], [class*='bet-type']"
        ).all()

        for section in market_sections:
            try:
                header = section.locator(
                    "[class*='market-name'], [class*='title'], h3, h4, span"
                ).first.text_content().strip().lower()

                odds_els = section.locator(
                    "[class*='odd'], [class*='price'], [class*='outcome'], "
                    "[class*='coeff'], button"
                ).all()
                vals = []
                labels = []
                for el in odds_els:
                    txt = el.text_content().strip()
                    try:
                        v = float(txt)
                        if 1.01 <= v <= 99:
                            vals.append(v)
                    except ValueError:
                        if txt and len(txt) < 20 and not txt.replace(".","").isdigit():
                            labels.append(txt)

                if not vals:
                    continue

                # Map known market names
                if any(x in header for x in ["1x2", "match result", "full time", "ft result"]):
                    if len(vals) == 3:
                        markets["FT_1X2"] = {"home": vals[0], "draw": vals[1], "away": vals[2]}
                    elif len(vals) == 2:
                        markets["H2H"] = {"home": vals[0], "away": vals[1]}

                elif any(x in header for x in ["winner", "match winner", "money line", "to win"]):
                    if len(vals) == 2:
                        markets["H2H"] = {"home": vals[0], "away": vals[1]}

                elif any(x in header for x in ["over/under 2.5", "total 2.5", "o/u 2.5"]):
                    if len(vals) == 2:
                        markets["OU25"] = {"over": vals[0], "under": vals[1]}

                elif any(x in header for x in ["over/under 1.5", "total 1.5"]):
                    if len(vals) == 2:
                        markets["OU15"] = {"over": vals[0], "under": vals[1]}

                elif any(x in header for x in ["over/under 3.5", "total 3.5"]):
                    if len(vals) == 2:
                        markets["OU35"] = {"over": vals[0], "under": vals[1]}

                elif any(x in header for x in ["both teams", "btts", "gg/ng", "both score"]):
                    if len(vals) == 2:
                        markets["BTTS"] = {"yes": vals[0], "no": vals[1]}

                elif any(x in header for x in ["double chance"]):
                    if len(vals) == 3:
                        markets["DC"] = {"1X": vals[0], "12": vals[1], "X2": vals[2]}

                elif any(x in header for x in ["draw no bet", "dnb"]):
                    if len(vals) == 2:
                        markets["DNB"] = {"home": vals[0], "away": vals[1]}

                elif any(x in header for x in ["asian handicap", "handicap"]):
                    if len(vals) == 2:
                        markets["AH"] = {"home": vals[0], "away": vals[1]}

                elif any(x in header for x in ["correct score"]):
                    if vals:
                        markets["CS"] = {f"sc_{i}": v for i, v in enumerate(vals[:9])}

                elif any(x in header for x in ["half time", "ht result", "1st half"]):
                    if len(vals) == 3:
                        markets["HT_1X2"] = {"home": vals[0], "draw": vals[1], "away": vals[2]}
                    elif len(vals) == 2:
                        markets["HT_H2H"] = {"home": vals[0], "away": vals[1]}

                elif any(x in header for x in ["set winner", "set 1", "first set"]):
                    if len(vals) == 2:
                        markets["SET1"] = {"home": vals[0], "away": vals[1]}

                elif any(x in header for x in ["total games", "total sets"]):
                    if len(vals) == 2:
                        markets["TOTAL_GAMES"] = {"over": vals[0], "under": vals[1]}

            except Exception:
                continue

        return markets

    #  Quick extract from listing row (no deep click) 

    def _extract_from_row(self, row, market_type) -> dict:
        all_texts = row.locator("span, div, p, td, a").all_text_contents()
        team_candidates = [t.strip() for t in all_texts if is_team_name(t.strip())]

        seen = []
        for t in team_candidates:
            if t not in seen:
                seen.append(t)
        if len(seen) < 2:
            return None

        home, away = seen[0], seen[1]

        odds_els = row.locator(
            "[class*='odd'], [class*='price'], [class*='outcome'], "
            "button[data-odd], [class*='coeff'], [class*='val']"
        ).all()
        odds_vals = []
        for el in odds_els:
            txt = el.text_content().strip()
            try:
                v = float(txt)
                if 1.01 <= v <= 50:
                    odds_vals.append(v)
            except ValueError:
                continue

        if len(odds_vals) < 2:
            return None

        result = {"home": home, "away": away, "sport": "football",
                  "source": "betika", "markets": {}}

        if market_type == "3way" and len(odds_vals) >= 3:
            result["markets"]["FT_1X2"] = {
                "home": odds_vals[0], "draw": odds_vals[1], "away": odds_vals[2]
            }
            if len(odds_vals) >= 5:
                result["markets"]["OU25"] = {"over": odds_vals[3], "under": odds_vals[4]}
            if len(odds_vals) >= 7:
                result["markets"]["BTTS"] = {"yes": odds_vals[5], "no": odds_vals[6]}

        elif market_type == "2way" and len(odds_vals) >= 2:
            result["markets"]["H2H"] = {"home": odds_vals[0], "away": odds_vals[1]}
            if len(odds_vals) >= 4:
                result["markets"]["OU25"] = {"over": odds_vals[2], "under": odds_vals[3]}

        return result
