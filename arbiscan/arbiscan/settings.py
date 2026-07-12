import environ
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY    = env("SECRET_KEY")
DEBUG         = env("DEBUG")
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "odds.apps.OddsConfig",
    "accounts.apps.AccountsConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF     = "arbiscan.urls"
WSGI_APPLICATION = "arbiscan.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

from datetime import timedelta
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# CORS - allow the Vite dev server (and any configured origins) to call the API.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:5173", "http://127.0.0.1:5173"],
)

STATIC_URL         = "/static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ODDSPAPI_KEY        = env("ODDSPAPI_KEY",        default="")
THE_ODDS_API_KEY    = env("THE_ODDS_API_KEY",    default="")
DEFAULT_BANKROLL    = env.float("DEFAULT_BANKROLL",    default=10000)
NEAR_MISS_THRESHOLD = env.float("NEAR_MISS_THRESHOLD", default=3.0)
ARB_MIN_PROFIT      = env.float("ARB_MIN_PROFIT",      default=0.0)

ODDSPAPI_BASE = "https://api.oddspapi.io/v4"
THEODDS_BASE  = "https://api.the-odds-api.com/v4"

TOURNAMENT_MAP = {
    "ucl":        ("7",   "UEFA Champions League"),
    "epl":        ("17",  "English Premier League"),
    "laliga":     ("8",   "LaLiga"),
    "bundesliga": ("37",  "Bundesliga"),
    "seriea":     ("23",  "Serie A"),
    "ligue1":     ("34",  "Ligue 1"),
    "eredivisie": ("54",  "Eredivisie"),
    "superlig":   ("132", "Super Lig"),
    "europa":       ("6",    "UEFA Europa League"),
    "confleague":   ("2486", "UEFA Conference League"),
    "championship": ("18",   "EFL Championship"),
    "liga_mx":      ("57",   "Liga MX"),
    "primeira":     ("238",  "Primeira Liga"),
    "scottish_pl":  ("179",  "Scottish Premiership"),
    "jupiler":      ("11",   "Jupiler Pro League"),
    "allsvenskan":  ("63",   "Allsvenskan"),
    "fa_cup":       ("1243", "FA Cup"),

}

# --- Sport-aware config for 2-way cross-book arbitrage (new pipeline) ---
# Each sport drives the interactive `arb` command.
#   sport_id    : OddsPapi sportId (resolved via discovery, see _probe / discover_all_leagues)
#   market      : BookmakerOdds market label the scanner pairs across books
#   type        : "2way" (H2H home/away) or "3way" (FT_1X2 home/draw/away)
#   books       : recommended bookmakers auto-selected for this sport (cross-book pool)
#   name_filter : optional substrings to prefer main-tour tournaments (e.g. ATP/WTA over ITF)
#   tournaments : optional fixed {slug: (api_id, name)}; if omitted the `arb` command
#                 fetches the live list of currently-active tournaments at runtime
#                 (tennis/MMA events rotate weekly, so static IDs would go stale).
SPORTS = {
    "tennis": {
        "name": "Tennis", "sport_id": 12, "market": "H2H", "type": "2way",
        "books": ["pinnacle", "bet365", "1xbet", "betsson", "unibet", "betika"],
        "name_filter": ["ATP", "WTA"],
    },
    "basketball": {
        "name": "Basketball", "sport_id": 11, "market": "H2H", "type": "2way",
        "books": ["pinnacle", "bet365", "1xbet", "betsson", "unibet"],
        "name_filter": [],
    },
    "mma": {
        "name": "MMA / UFC", "sport_id": 20, "market": "H2H", "type": "2way",
        "books": ["pinnacle", "bet365", "1xbet", "betsson", "unibet"],
        "name_filter": ["UFC", "PFL", "Bellator"],
    },
    "worldcup": {
        "name": "FIFA World Cup", "sport_id": 10, "market": "FT_1X2", "type": "3way",
        "books": ["pinnacle", "bet365", "1xbet", "betsson", "unibet", "betika"],
        "tournaments": {"worldcup": ("16", "FIFA World Cup")},
    },
}

# --- Arbitrage sanity guards (reject corrupted/stale data that fabricates fake arbs) ---
ODDS_LEG_CAP      = env.float("ODDS_LEG_CAP",      default=50.0)   # reject any single leg priced above this
ARB_MAX_MARGIN    = env.float("ARB_MAX_MARGIN",    default=0.15)   # >15% "profit" => almost surely a data error
ARB_FRESH_MINUTES = env.int("ARB_FRESH_MINUTES",   default=180)    # only scan odds fetched within N minutes

# Freemium: free users see arbs up to this ROI%; higher-profit ones are locked.
FREE_ARB_ROI_CAP  = env.float("FREE_ARB_ROI_CAP",  default=1.0)

USE_TZ = True

BETIKA_PHONE    = env("BETIKA_PHONE",    default="")
BETIKA_PASSWORD = env("BETIKA_PASSWORD", default="")
BETIKA_HEADLESS = env.bool("BETIKA_HEADLESS", default=True)
