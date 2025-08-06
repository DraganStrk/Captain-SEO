import os
import csv
from google.cloud import storage
from keyword_analyzer import analyze_keyword
from bucket_handler import read_phrases_from_bucket, upload_file_to_bucket

# === PODESAVANJA ===
BUCKET_NAME = "captain-seo-keywords"
KEYWORDS_FILE = "keywords.txt"
PROCESSED_LOG_FILE = "data/processed_log.txt"
RESULTS_FILE = "results.csv"
NUM_PHRASES_PER_RUN = 5
FIELDNAMES = ["keyword", "avg_searches", "competition"]

# === Kreiraj folder ako ne postoji ===
os.makedirs("data", exist_ok=True)

# === Učitaj već obrađene fraze ===
if os.path.exists(PROCESSED_LOG_FILE):
    with open(PROCESSED_LOG_FILE, "r", encoding="utf-8") as f:
        processed = set(line.strip() for line in f)
else:
    processed = set()

# === Učitaj fraze iz bucket-a ===
phrases = read_phrases_from_bucket(BUCKET_NAME, KEYWORDS_FILE)
new_phrases = [phrase for phrase in phrases if phrase not in processed][:NUM_PHRASES_PER_RUN]

print(f"[Captain SEO] Pronađene fraze: {new_phrases}")

# === Analiziraj nove fraze ===
results = []

for phrase in new_phrases:
    print(f"🎯 Obrada fraze: {phrase}")
    data = analyze_keyword(phrase)

    # Zadrži samo očekivana polja
    filtered = {k: data[k] for k in FIELDNAMES if k in data}
    results.append(filtered)

    processed.add(phrase)

# === Snimi rezultate u CSV ===
with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
    writer.writeheader()
    for row in results:
        writer.writerow(row)

# === Uploaduj CSV u bucket ===
upload_file_to_bucket(BUCKET_NAME, RESULTS_FILE, RESULTS_FILE)

# === Ažuriraj log obrađenih fraza ===
with open(PROCESSED_LOG_FILE, "w", encoding="utf-8") as f:
    for p in sorted(processed):
        f.write(p + "\n")

print("✅ Rezultati su uspešno sačuvani i uploadovani.")
