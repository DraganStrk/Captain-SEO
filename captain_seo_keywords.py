import os
import csv
import json
import time
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# === 1. Kreiraj credentials.json ako postoji secret iz env ===
credentials_content = os.getenv("GOOGLE_ADS_CREDENTIALS")
if credentials_content:
    with open("credentials.json", "w") as f:
        f.write(credentials_content)

# === 2. Konfigurisanje ===
FRAZE_FAJL = "phrases.txt"         # Fajl sa frazama (po jedna u svakom redu)
LOG_FAJL = "last_run.log"          # Fajl sa već obrađenim frazama
REZULTAT_FAJL = "results.csv"      # CSV rezultat
MAX_OBRADA = 5                     # Broj fraza po pokretanju

# === 3. Učitavanje klijenta ===
client = GoogleAdsClient.load_from_storage("credentials.json")

# === 4. Učitavanje fraza ===
with open(FRAZE_FAJL, "r", encoding="utf-8") as f:
    sve_fraze = [line.strip() for line in f if line.strip()]

# === 5. Učitavanje loga ===
if os.path.exists(LOG_FAJL):
    with open(LOG_FAJL, "r", encoding="utf-8") as f:
        obradjene = set(line.strip() for line in f)
else:
    obradjene = set()

# === 6. Filtriranje fraza ===
nove_fraze = [fraza for fraza in sve_fraze if fraza not in obradjene][:MAX_OBRADA]

if not nove_fraze:
    print("Nema novih fraza za obradu.")
    exit(0)

# === 7. Funkcija za dohvat statistike ===
def dohvati_keyword_stats(fraza):
    try:
        service = client.get_service("KeywordPlanIdeaService")
        keyword_seed = client.get_type("KeywordSeed")
        keyword_seed.keywords.append(fraza)

        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = "4034856713"
        request.keyword_seed = keyword_seed
        request.geo_target_constants.append("geoTargetConstants/2840")  # US
        request.language = "languageConstants/1000"  # English
        request.include_adult_keywords = False

        response = service.generate_keyword_ideas(request=request)
        for idea in response:
            return {
                "keyword": idea.text,
                "avg_monthly_searches": idea.keyword_idea_metrics.avg_monthly_searches,
                "competition": idea.keyword_idea_metrics.competition.name,
                "low_top_of_page_bid": idea.keyword_idea_metrics.low_top_of_page_bid_micros / 1_000_000,
                "high_top_of_page_bid": idea.keyword_idea_metrics.high_top_of_page_bid_micros / 1_000_000,
            }

    except GoogleAdsException as ex:
        print(f"Greška za frazu: {fraza} – {ex}")
        return None

# === 8. Obrada fraza i upis rezultata ===
rezultati = []

for fraza in nove_fraze:
    print(f"Obrađujem: {fraza}")
    rezultat = dohvati_keyword_stats(fraza)
    if rezultat:
        rezultati.append(rezultat)
    time.sleep(1)

# === 9. Upis rezultata u CSV ===
polja = ["keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid"]

file_exists = os.path.exists(REZULTAT_FAJL)
with open(REZULTAT_FAJL, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=polja)
    if not file_exists:
        writer.writeheader()
    writer.writerows(rezultati)

# === 10. Ažuriranje loga ===
with open(LOG_FAJL, "a", encoding="utf-8") as f:
    for fraza in nove_fraze:
        f.write(fraza + "\n")

print(f"Završeno. Obradjeno: {len(nove_fraze)} fraza.")
