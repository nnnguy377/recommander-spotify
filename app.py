import pandas as pd
import requests
import base64
import time
import os
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# === PARAMÈTRES ===
CLIENT_ID = "VOTRE_CLIENT_ID"
CLIENT_SECRET = "VOTRE_CLIENT_SECRET"
INPUT_PATH = "datasets/artists_gp6.dat"
USER_ARTISTS_PATH = "datasets/user_artists_gp6.dat"
SLEEP_TIME = 0.2  # pause entre requêtes pour éviter les limites

# === FONCTION : Obtenir un token d'accès Spotify ===
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
        print("Erreur récupération token :", response.text)
        return None

# === FONCTION : Chercher l'ID Spotify d'un artiste ===
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

# === FONCTION : Obtenir les genres d'un artiste ===
def get_artist_genres(artist_id, token):
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("genres", [])
    return []

# === ENRICHISSEMENT DES GENRES ===
def enrich_artists(filepath, token):
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        return pd.DataFrame()

    df = pd.read_csv(filepath, sep="\t")
    genres_list = []
    null_count = 0

    print("🔍 Extraction des genres Spotify pour chaque artiste...")
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

# === PHASE 1 : ENRICHISSEMENT ===
print("📦 Phase 1 : Enrichissement du fichier artistes...")
token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
if token:
    enrich_artists(INPUT_PATH, token)
else:
    print("❌ Token Spotify non récupéré. Vérifiez vos identifiants.")
    exit()

# === PHASE 2 : LANCEMENT DE L'APPLICATION STREAMLIT ===
print("🚀 Phase 2 : Lancement du moteur de recommandation Streamlit...")
os.system("streamlit run app.py")
