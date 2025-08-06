import argparse
import csv
import os
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# === UCITAJ ENV VARIJABLE ===
load_dotenv()

developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")

# === ARGUMENTI ===
parser = argparse.ArgumentParser(description="Captain SEO Keyword Generator")
parser.add_argument("--theme", type=str, help="Main topic to generate seed phrases from phrases.txt")
parser.add_argument("--phrases_file", type=str, help="Path to TXT/CSV file with seed phrases (optional)")
parser.add_argument("--min_search", type=int, default=1000, help="Minimum monthly search volume")
parser.add_argument("--limit", type=int, default=100, help="Maximum number of keyword results to return")
args = parser.parse_args()

# === FUNKCIJE ===

def read_last_run_log():
    if not os.path.exists("last_run.log"):
        return set()
    with open("last_run.log", "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

def update_last_run_log(phrases):
    with open("last_run.log", "a", encoding="utf-8") as f:
        for phrase in phrases:
            f.write(phrase + "\n")

def generate_seed_keywords(theme, template_file="phrases.txt"):
    if not os.path.exists(template_file):
        print("❌ Template file phrases.txt not found.")
        exit(1)
    with open(template_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip().replace("{theme}", theme.strip()) for line in lines if "{theme}" in line]

def load_phrases():
    if args.theme:
        return generate_seed_keywords(args.theme)
    elif args.phrases_file and os.path.exists(args.phrases_file):
        with open(args.phrases_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    else:
        print("❌ Must provide either --theme or --phrases_file.")
        exit(1)

def init_google_ads_client():
    return GoogleAdsClient.load_from_dict({
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "login_customer_id": customer_id,
    })

# === GLAVNA FUNKCIJA ===

def main():
    already_done = read_last_run_log()
    seed_phrases = load_phrases()
    to_process = [phrase for phrase in seed_phrases if phrase not in already_done][:args.limit]

    print(f"🔍 Generating keywords for {len(to_process)} new seed phrases...")

    client = init_google_ads_client()
    keyword_service = client.get_service("KeywordPlanIdeaService")

    keyword_ideas = []

    for phrase in to_process:
        try:
            response = keyword_service.generate_keyword_ideas(
                customer_id=customer_id,
                language="1000",  # English
                geo_target_constants=["2840"],  # USA
                keyword_plan_network=1,  # GOOGLE_SEARCH
                keyword_seed={"keywords": [phrase]},
            )

            for idea in response:
                text = idea.text
                volume = idea.keyword_idea_metrics.avg_monthly_searches
                competition = idea.keyword_idea_metrics.competition.name
                cpc_micros = idea.keyword_idea_metrics.high_top_of_page_bid_micros or 0
                cpc = round(cpc_micros / 1_000_000, 2)

                if volume >= args.min_search and len(text.split()) >= 3:
                    keyword_ideas.append((text, volume, competition, cpc))

        except GoogleAdsException as ex:
            print(f"⚠️ Error for phrase '{phrase}': {ex}")

    print(f"✅ Found {len(keyword_ideas)} keywords with search volume ≥ {args.min_search}.")

    # Snimi rezultate
    with open("results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Keyword", "Search Volume", "Competition", "CPC (USD)"])
        for row in keyword_ideas[:args.limit]:
            writer.writerow(row)

    # Ažuriraj log
    update_last_run_log(to_process)
    print("📦 Saved to results.csv and updated last_run.log.")

if __name__ == "__main__":
    main()
