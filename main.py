from keyword_analyzer import run_keyword_analysis
import os
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

def captain_seo_entrypoint(request):
    run_keyword_analysis()
    return 'Captain SEO finished keyword analysis.'
