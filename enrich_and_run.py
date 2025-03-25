# enrich_and_run.py

import pandas as pd
import requests
import base64
import time
import os

# === PARAMÈTRES ===
CLIENT_ID = "c284ca8f68794e6f84c8c62f6f26efc0"
CLIENT_SECRET = "1f4917a93a024c9fbab79b3982df6076"
INPUT_PATH = "datasets/artists_gp6.dat"
SLEEP_TIME = 0.4

# === FONCTIONS ===
def get_spotify_token(client_id, client_secret):
    url = "https://accounts.spotify.com/api/token"
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        print("❌ Erreur de récupération du token :", response.text)
        return None

def get_spotify_artist_id(artist_name, token):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": artist_name, "type": "artist", "limit": 1}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        items = response.json()["artists"]["items"]
        if items:
            return items[0]["id"]
    return None

def get_artist_genres(artist_id, token):
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("genres", [])
    return []

def enrich_artists(filepath, token):
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        return pd.DataFrame()
    df = pd.read_csv(filepath, sep="\t")
    genres_list = []
    null_count = 0
    print("🔍 Enrichissement des artistes Spotify avec leurs genres...\n")
    for name in df["name"]:
        artist_id = get_spotify_artist_id(name, token)
        if artist_id:
            genres = get_artist_genres(artist_id, token)
        else:
            genres = []
            null_count += 1
        genres_list.append(", ".join(genres))
        print(f"🎵 {name} → {', '.join(genres) if genres else 'Genres non trouvés'}")
        time.sleep(SLEEP_TIME)
    df["genres"] = genres_list
    df.to_csv(filepath, sep="\t", index=False)
    print(f"\n✅ Enrichissement terminé : {len(df) - null_count}/{len(df)} artistes avec genres.")
    return df

# === EXECUTION ===
print("📦 PHASE 1 : ENRICHISSEMENT DU FICHIER")
token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
if token:
    enrich_artists(INPUT_PATH, token)
else:
    print("❌ Impossible de récupérer le token Spotify.")
    exit()

print("\n🚀 PHASE 2 : LANCEMENT DE L'APPLICATION STREAMLIT")
os.system("python3 -m streamlit run app_1.py")
