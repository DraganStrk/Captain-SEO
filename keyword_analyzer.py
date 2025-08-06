def analyze_keyword(keyword):
    # Ovde je dummy analiza, simulacija
    # Kasnije ćemo ovo povezati sa realnim podacima iz Google Ads API
    import random

    avg_searches = random.randint(0, 10000)
    competition = round(random.uniform(0.0, 1.0), 2)

    return {
        "keyword": keyword,
        "avg_searches": avg_searches,
        "competition": competition
    }
