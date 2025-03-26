import requests
import base64
import pandas as pd
import time
import unicodedata
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# === PARAMÈTRES ===
CLIENT_ID = "d4e773279f59451d94129c72d21595b5"
CLIENT_SECRET = "341a32fea02246f29ff6ce7f3b552367"
INPUT_PATH = "datasets/artists_gp6.dat"
MAX_WORKERS = 5
SLEEP_TIME = 0.5

# === OBTENTION DU TOKEN ===
def get_token():
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode(),
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, headers=headers, data=data)
    return r.json().get("access_token")

# === NETTOYAGE DU NOM ===
def normalize_name(name):
    name = name.strip()
    name = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode("utf-8")
    name = re.sub(r"[^a-zA-Z0-9\s]", "", name)
    return name

# === RECHERCHE NOM SPOTIFY ===
def fetch_spotify_name(original_name, token):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    queries = [f"artist:\"{original_name}\"", original_name, normalize_name(original_name)]

    for query in queries:
        params = {"q": query, "type": "artist", "limit": 1}
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 429:
            retry = int(r.headers.get("Retry-After", 1))
            time.sleep(retry)
            continue
        if r.status_code != 200:
            continue
        items = r.json().get("artists", {}).get("items", [])
        if items:
            return items[0]["name"]
    return ""

# === TRAITEMENT PAR THREAD ===
def process_name(name, token):
    spot_name = fetch_spotify_name(name, token)
    time.sleep(SLEEP_TIME)
    return name, spot_name

# === SCRIPT PRINCIPAL ===
def extract_spotify_names():
    df = pd.read_csv(INPUT_PATH, sep="\t")
    names = df["name"].tolist()
    token = get_token()
    if not token:
        print("❌ Token invalide.")
        return

    results = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_name, name, token): name for name in names}
        for future in tqdm(as_completed(futures), total=len(futures), desc="🔍 Extraction noms Spotify"):
            name, spot_name = future.result()
            results[name] = spot_name

    df["spotify_name"] = df["name"].map(results)
    df.to_csv(INPUT_PATH, sep="\t", index=False)
    print("✅ Colonne 'spotify_name' ajoutée avec succès.")

if __name__ == "__main__":
    extract_spotify_names()
