import requests
import base64
import time
import pandas as pd
import os
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

# === PARAMÈTRES ===
CLIENT_ID = "6e820dc6d1f446b28d4e1804aca58858"
CLIENT_SECRET = "16fdc304ae6e4bfe883129405c65d136"
INPUT_PATH = "datasets/artists_gp6.dat"
CACHE_PATH = "artist_name_to_id.csv"
BATCH_SIZE = 50
MAX_WORKERS = 4
MAX_RETRIES = 3
SPOTIFY_TOKEN = None

# === AUTHENTIFICATION ===
def get_token():
    global SPOTIFY_TOKEN
    url = "https://accounts.spotify.com/api/token"
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, headers=headers, data=data)
    if r.status_code == 200:
        SPOTIFY_TOKEN = r.json()["access_token"]
    else:
        print("❌ Erreur récupération token:", r.text)
        SPOTIFY_TOKEN = None

# === CHARGER CACHE NOM -> ID ===
def load_cache():
    if os.path.exists(CACHE_PATH):
        return pd.read_csv(CACHE_PATH).set_index("name")["id"].to_dict()
    return {}

def save_cache(cache):
    pd.DataFrame([{"name": k, "id": v} for k, v in cache.items()]).to_csv(CACHE_PATH, index=False)

# === RECHERCHE ID + CACHE ===
def get_artist_id(name, cache):
    if name in cache:
        return cache[name]

    global SPOTIFY_TOKEN
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}

    params = {"q": name, "type": "artist", "limit": 3}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code == 401:
        get_token()
        return get_artist_id(name, cache)
    if r.status_code != 200:
        cache[name] = "NOT_FOUND"
        return None

    items = r.json().get("artists", {}).get("items", [])
    if items:
        best = max(items, key=lambda x: x.get("followers", {}).get("total", 0))
        cache[name] = best["id"]
        return best["id"]

    cache[name] = "NOT_FOUND"
    return None

# === REQUÊTE BATCH AVEC RETRIES ===
def get_genres_batch(artist_ids):
    global SPOTIFY_TOKEN
    url = "https://api.spotify.com/v1/artists"
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    params = {"ids": ",".join(artist_ids)}

    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 200:
            data = r.json().get("artists", [])
            return {a["id"]: a.get("genres", []) for a in data}
        elif r.status_code == 401:
            get_token()
        elif r.status_code == 429:
            retry = int(r.headers.get("Retry-After", 1))
            print(f"⏳ Too many requests. Waiting {retry}s...")
            time.sleep(retry)
        elif r.status_code == 500:
            print(f"⚠️ Erreur 500 (tentative {attempt}/{MAX_RETRIES}). Attente 2s...")
            time.sleep(2)
        else:
            print("❌ Erreur batch:", r.text)
            break

    return {}

# === TRAITEMENT PAR BATCH ===
def process_batch(names, cache):
    id_map = {}
    for name in names:
        artist_id = get_artist_id(name, cache)
        if artist_id:
            id_map[name] = artist_id
        else:
            print(f"❌ ID non trouvé pour {name}")
    genres_map = get_genres_batch([id for id in id_map.values() if id != "NOT_FOUND"])
    return {name: ", ".join(genres_map.get(artist_id, [])) for name, artist_id in id_map.items() if artist_id != "NOT_FOUND"}

# === MAIN ===
def enrich_all():
    get_token()
    if not SPOTIFY_TOKEN:
        print("❌ Token introuvable")
        return

    df = pd.read_csv(INPUT_PATH, sep="\t")
    df = df.drop(columns=[col for col in ["url", "pictureURL"] if col in df.columns], errors="ignore")

    if "genres" not in df.columns:
        df["genres"] = ""

    if "spotify_name" not in df.columns:
        print("❌ Colonne 'spotify_name' manquante. Veuillez d'abord l'extraire.")
        return

    to_process = df[df["genres"].isnull() | (df["genres"] == "")]["spotify_name"].tolist()
    print(f"🎯 {len(to_process)} artistes à enrichir via 'spotify_name'")

    cache = load_cache()
    batches = [to_process[i:i+BATCH_SIZE] for i in range(0, len(to_process), BATCH_SIZE)]
    total_batches = len(batches)
    enriched = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_batch, batch, cache): idx for idx, batch in enumerate(batches)}
        for future in as_completed(futures):
            batch_index = futures[future] + 1
            try:
                result = future.result()
                enriched.update(result)
                print(f"✅ Batch {batch_index}/{total_batches} terminé")
            except Exception as e:
                print(f"❌ Erreur batch {batch_index}: {e}")

    df["genres"] = df.apply(lambda row: enriched.get(row["spotify_name"], row.get("genres", "")), axis=1)
    df.to_csv(INPUT_PATH, sep="\t", index=False)
    save_cache(cache)

    not_found = {k: v for k, v in cache.items() if v == "NOT_FOUND"}
    if not_found:
        pd.DataFrame([{"name": k, "id": ""} for k in not_found]).to_csv("missing_artists_to_fix.csv", index=False)
        print(f"⚠️ {len(not_found)} artistes non trouvés. Corrigez-les dans 'missing_artists_to_fix.csv'")

    print("✅ Enrichissement terminé et fichier sauvegardé")

if __name__ == "__main__":
    enrich_all()
