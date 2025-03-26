import pandas as pd
import requests
import base64
import time
import os
import math
import re

# === PARAMÈTRES ===
CLIENT_ID = "e1b60679e9174eaab3bf06f31490ed75"
CLIENT_SECRET = "775e9a6153fc4093a896664fe4bb7d17"
INPUT_PATH = "datasets/artists_gp6.dat"
SLEEP_TIME = 0.5
BATCH_SIZE = 50

# === FONCTIONS D'AUTHENTIFICATION ===
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
        print("❌ Erreur récupération token:", response.text)
        return None

# === FONCTION : Nettoyage du nom ===
def clean_artist_name(name):
    name = name.strip()
    name = re.sub(r"[^a-zA-Z0-9 &]", "", name)  # enlever caractères spéciaux
    return name

# === FONCTION : Recherche robuste d'ID ===
def get_spotify_artist_id(artist_name, token):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}

    # Étape 1 : recherche stricte
    params_strict = {"q": f"artist:\"{artist_name}\"", "type": "artist", "limit": 1}
    response = requests.get(url, headers=headers, params=params_strict)
    if response.status_code == 200:
        items = response.json().get("artists", {}).get("items", [])
        if items:
            return items[0]["id"]
    elif response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "1"))
        print(f"⏳ Trop de requêtes. Attente {retry_after}s...")
        time.sleep(retry_after)
        return get_spotify_artist_id(artist_name, token)

    # Étape 2 : tentative normale
    params_loose = {"q": artist_name, "type": "artist", "limit": 1}
    response = requests.get(url, headers=headers, params=params_loose)
    if response.status_code == 200:
        items = response.json().get("artists", {}).get("items", [])
        if items:
            return items[0]["id"]
    elif response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "1"))
        print(f"⏳ Trop de requêtes (loose). Attente {retry_after}s...")
        time.sleep(retry_after)
        return get_spotify_artist_id(artist_name, token)

    return None

# === FONCTION : Obtenir les genres de plusieurs artistes ===
def get_artists_genres_batch(artist_ids, token):
    url = f"https://api.spotify.com/v1/artists"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"ids": ",".join(artist_ids)}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        artists_info = response.json().get("artists", [])
        return {artist["id"]: artist.get("genres", []) for artist in artists_info}
    elif response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "1"))
        print(f"⏳ Trop de requêtes batch. Attente {retry_after}s...")
        time.sleep(retry_after)
        return get_artists_genres_batch(artist_ids, token)
    else:
        print("❌ Erreur batch genres:", response.text)
    return {}

# === ENRICHISSEMENT DES GENRES PAR LOTS AVEC SAUVEGARDE PROGRESSIVE ===
def enrich_artists(filepath, token):
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable : {filepath}")
        return pd.DataFrame()

    df = pd.read_csv(filepath, sep="\t")

    if "genres" not in df.columns:
        df["genres"] = ""

    print("🔍 Filtrage des artistes sans genres...")
    df_to_enrich = df[df["genres"].isnull() | (df["genres"] == "")]

    if df_to_enrich.empty:
        print("✅ Tous les artistes ont déjà des genres. Rien à faire.")
        return df

    print("🔍 Récupération des IDs Spotify pour les artistes à enrichir...")
    artist_id_map = {}
    for name in df_to_enrich["name"]:
        cleaned_name = clean_artist_name(name)
        artist_id = get_spotify_artist_id(cleaned_name, token)
        if artist_id:
            artist_id_map[name] = artist_id
        else:
            print(f"❌ ID non trouvé pour {name}")
        time.sleep(SLEEP_TIME)

    print("📦 Traitement par lots de 50 artistes...")
    all_genres = {}
    artist_id_list = list(artist_id_map.values())
    for i in range(0, len(artist_id_list), BATCH_SIZE):
        batch_ids = artist_id_list[i:i+BATCH_SIZE]
        batch_genres = get_artists_genres_batch(batch_ids, token)
        all_genres.update(batch_genres)

        print(f"✅ Batch {i//BATCH_SIZE + 1}/{math.ceil(len(artist_id_list)/BATCH_SIZE)} terminé")

        enriched_names = [name for name, aid in artist_id_map.items() if aid in batch_genres]
        for name in enriched_names:
            genres_str = ", ".join(batch_genres[artist_id_map[name]])
            df.loc[df["name"] == name, "genres"] = genres_str

        df.to_csv(filepath, sep="\t", index=False)
        time.sleep(SLEEP_TIME)

    print("✅ Enregistrement finalisé dans le fichier.")
    return df

# === EXÉCUTION ===
print("📦 PHASE 1 : Enrichissement du fichier artistes...")
token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
if token:
    enrich_artists(INPUT_PATH, token)
else:
    print("❌ Token Spotify non récupéré. Vérifiez vos identifiants.")
    exit()

print("\n🚀 PHASE 2 : Lancement de l'application Streamlit...")
os.system("python3 -m streamlit run app_1.py")