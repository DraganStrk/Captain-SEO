import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/shtrk/OneDrive/fish-room/SEO/captain_seo_cloud/credentials/credentials.json"

from google.cloud import storage

import os

def read_phrases_from_bucket(bucket_name, file_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    content = blob.download_as_text()
    phrases = [line.strip() for line in content.splitlines() if line.strip()]
    return phrases

def upload_file_to_bucket(bucket_name, source_file_path, destination_blob_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"[Captain SEO] 📤 Fajl '{source_file_path}' je uspešno uploadovan kao '{destination_blob_name}' u bucket '{bucket_name}'.")
