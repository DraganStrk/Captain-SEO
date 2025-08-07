import os
import csv
import datetime
import time
from dotenv import load_dotenv

from google.oauth2 import service_account
import gspread
import google.api_core.exceptions
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

# === Google Ads API Quota ===
MAX_DAILY_UNITS = 15000  # default quota
UNITS_PER_CALL = 100     # KeywordPlanIdeaService.GenerateKeywordIdeas

# === LOAD ENV ===
load_dotenv()

developer_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")


def load_seed_phrases(filename, already_processed, limit):
    with open(filename, "r", encoding="utf-8") as file:
        phrases = [line.strip() for line in file if line.strip()]
    new_phrases = [p for p in phrases if p not in already_processed]
    return new_phrases[:limit]


def load_last_run_log(log_file):
    if not os.path.exists(log_file):
        return set()
    with open(log_file, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())


def save_last_run_log(log_file, phrases):
    with open(log_file, "a", encoding="utf-8") as f:
        for phrase in phrases:
            f.write(phrase + "\n")


def init_google_ads_client():
    return GoogleAdsClient.load_from_dict({
        "developer_token": developer_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "login_customer_id": customer_id,
        "use_proto_plus": True
    })


def fetch_keyword_ideas(client, customer_id, keyword_text, retries=3, delay=5):
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    language = "languageConstants/1000"  # English
    location = "geoTargetConstants/2840"  # USA

    request = {
        "customer_id": customer_id,
        "language": language,
        "geo_target_constants": [location],
        "keyword_plan_network": client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH,
        "keyword_seed": {"keywords": [keyword_text]},
    }

    for attempt in range(retries):
        try:
            response = keyword_plan_idea_service.generate_keyword_ideas(request=request)
            time.sleep(delay)
            return response
        except google.api_core.exceptions.ResourceExhausted:
            print(f"⚠️ Quota exhausted. Retrying in {delay} seconds... (attempt {attempt + 1}/{retries})")
            time.sleep(delay)
        except google.api_core.exceptions.GoogleAPICallError as e:
            print(f"❌ API call error: {e}")
            break
    return None


def write_to_csv(keywords, filename="results.csv"):
    file_exists = os.path.isfile(filename)
    with open(filename, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["Keyword", "Search Volume", "Competition", "CPC", "Seed Phrase", "Date"])
        for row in keywords:
            writer.writerow(row)


def append_to_google_sheet(all_results, sheet_name, service_account_file):
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)

    import gspread_formatting as gsf

    gc = gspread.authorize(creds)

    try:
        sheet = gc.open(sheet_name).sheet1
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ Google Sheet '{sheet_name}' not found.")
        return

    existing = sheet.get_all_values()

    # Ako je sheet prazan, dodaj zaglavlja
    if not existing:
        header = ["Keyword", "Search Volume", "Competition", "CPC", "Seed Phrase", "Date"]
        sheet.append_row(header, value_input_option='USER_ENTERED')

        # Formatiraj zaglavlje (bold + siva pozadina)
        fmt = gsf.cellFormat(
            backgroundColor=gsf.color(0.9, 0.9, 0.9),
            textFormat=gsf.textFormat(bold=True),
            horizontalAlignment='CENTER'
        )
        gsf.format_cell_range(sheet, 'A1:F1', fmt)

    # Dodaj podatke
    for row in all_results:
        sheet.append_row(row, value_input_option='USER_ENTERED')

    print(f"🟢 Appended {len(all_results)} rows to Google Sheet '{sheet_name}'.")



def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True)
    parser.add_argument("--min_search", type=int, default=1000)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    # === API LIMIT GUARD ===
    max_calls = MAX_DAILY_UNITS // UNITS_PER_CALL
    if args.limit > max_calls:
        print(f"⚠️ API limit: You requested {args.limit} phrases, but max allowed is {max_calls}. Reducing to {max_calls}.")
        args.limit = max_calls

    # === Custom definitions ===
    sheet_name = f"Captain SEO Fishing Keywords"  # You can add date if needed
    service_account_file = "google_sheet_credentials.json"  # Adjust if your file has a different name

    # === Load seed phrases ===
    already_processed = load_last_run_log("data/last_run.log")
    templates = load_seed_phrases("phrases.txt", already_processed, args.limit)
    filled_phrases = [tpl.format(theme=args.theme) for tpl in templates]

    if not filled_phrases:
        print("⚠️ No new phrases to process.")
        return

    print(f"🔍 Generating keywords for {len(filled_phrases)} phrases with theme '{args.theme}'...")

    client = init_google_ads_client()
    today = datetime.date.today().isoformat()
    all_results = []

    for phrase in filled_phrases:
        response = fetch_keyword_ideas(client, customer_id, phrase)
        if not response:
            continue
        for idea in response:
            volume = idea.keyword_idea_metrics.avg_monthly_searches
            if volume and volume >= args.min_search:
                competition = idea.keyword_idea_metrics.competition.name
                cpc = (idea.keyword_idea_metrics.high_top_of_page_bid_micros or 0) / 1_000_000
                all_results.append([
                    idea.text, volume, competition, round(cpc, 2), phrase, today
                ])

    if all_results:
        write_to_csv(all_results)
        append_to_google_sheet(all_results, sheet_name, service_account_file)
        save_last_run_log("data/last_run.log", templates)
        print(f"✅ Found {len(all_results)} keywords with search volume ≥ {args.min_search}.")
        print("📦 Saved to results.csv and updated last_run.log.")
    else:
        print("⚠️ No keywords met the criteria.")




main()
