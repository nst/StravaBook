from reportlab.lib.units import mm, cm

STANDARD_PORTRAIT = (205 * mm, 270 * mm)
BLEED = 0.3 * cm
w, h = STANDARD_PORTRAIT
STANDARD_PORTRAIT_BLEED = (w + 2*BLEED, h + 2*BLEED)

PAGES_DIR = "pages"

STRAVA_CLIENT_ID = ""
STRAVA_CLIENT_SECRET = ""

STADIA_API_KEY = ""
MAPTILER_API_KEY = ""
