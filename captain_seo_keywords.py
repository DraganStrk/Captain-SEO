import os
import csv
import time
import tempfile
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# === 1. Kreiraj privremeni credentials.yaml iz GitHub Secret-a ===
credentials_content = os.getenv("GOOGLE_ADS_CREDENTIALS")
if not credentials_content:
    raise Exception("Missing GOOGLE_ADS_CREDENTIALS environment variable.")

with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode="w") as temp_config:
    temp_config.write(credentials_content)
    temp_config_path = temp_config.name

# === 2. Učitaj Google Ads klijent ===
client = GoogleAdsClient.load_from_storage(temp_config_path)

# === 3. Podešavanja ===
PHRASES_FILE = "phrases.txt"
LOG_FILE = "last_run.log"
RESULTS_FILE = "results.csv"
MAX_KEYWORDS_PER_RUN = 5
CUSTOMER_ID = "4034856713"  # bez crtica

# === 4. Učitaj fraze ===
with open(PHRASES_FILE, "r", encoding="utf-8") as f:
    all_phrases = [line.strip() for line in f if line.strip()]

# === 5. Učitaj već obrađene fraze ===
if os.path.exists(LOG_FILE):
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        processed = set(line.strip() for line in f)
else:
    processed = set()

# === 6. Filtriraj nove fraze ===
new_phrases = [p for p in all_phrases if p not in processed][:MAX_KEYWORDS_PER_RUN]
if not new_phrases:
    print("Nema novih fraza za obradu.")
    exit(0)

# === 7. Funkcija za dohvat statistike ===
def fetch_keyword_data(phrase):
    try:
        service = client.get_service("KeywordPlanIdeaService")
        request = client.get_type("GenerateKeywordIdeasRequest")

        request.customer_id = CUSTOMER_ID
        request.language = "languageConstants/1000"  # English
        request.geo_target_constants.append("geoTargetConstants/2840")  # United States
        request.include_adult_keywords = False

        # Ispravno postavljanje fraze
        request.keyword_and_url_seed.keywords.append(phrase)

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
        print(f"Greška za frazu '{phrase}': {ex}")
        return None

# === 8. Obrada fraza ===
results = []

for phrase in new_phrases:
    print(f"Obrađujem: {phrase}")
    data = fetch_keyword_data(phrase)
    if data:
        results.append(data)
    time.sleep(1)  # izbegavanje prebrzih zahteva

# === 9. Upis rezultata u CSV ===
fields = ["keyword", "avg_monthly_searches", "competition", "low_top_of_page_bid", "high_top_of_page_bid"]
file_exists = os.path.exists(RESULTS_FILE)

with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    if not file_exists:
        writer.writeheader()
    writer.writerows(results)

# === 10. Ažuriraj log ===
with open(LOG_FILE, "a", encoding="utf-8") as f:
    for phrase in new_phrases:
        f.write(phrase + "\n")

print(f"Završeno. Obradjeno fraza: {len(new_phrases)}.")
