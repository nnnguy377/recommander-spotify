import pandas as pd
import streamlit as st
import requests
import base64
import time

# === CONFIG PAGE ===
st.set_page_config(page_title="Recommandations Spotify", layout="centered")
st.image("images/logo_spotify.png", width=200)
st.title("🎧 Recommandation d'artistes Spotify")

# === SIDEBAR : IDENTIFIANTS SPOTIFY ===
st.sidebar.header("🔐 Connexion Spotify API")
client_id = st.sidebar.text_input("Client ID")
client_secret = st.sidebar.text_input("Client Secret", type="password")

# === AUTH : RÉCUPÉRATION DU TOKEN (avec cache) ===
@st.cache_data(show_spinner=False)
def get_spotify_token(client_id, client_secret):
    url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        token = response.json()["access_token"]
        return token
    else:
        st.error("❌ Échec de la récupération du token Spotify.")
        return None

# === CONDITION POUR CONTINUER ===
if not client_id or not client_secret:
    st.warning("🛑 Veuillez entrer votre Client ID et Secret dans la barre latérale.")
    st.stop()

SPOTIFY_TOKEN = get_spotify_token(client_id, client_secret)
if not SPOTIFY_TOKEN:
    st.stop()

# === CHARGEMENT DES DONNÉES ===
@st.cache_data
def load_data():
    artists = pd.read_csv("datasets/artists_gp6.dat", sep="\t")
    user_artists = pd.read_csv("datasets/user_artists_gp6.dat", sep="\t")
    return artists, user_artists

artists, user_artists = load_data()

# === APPELS API SPOTIFY ===
def get_spotify_artist_id(artist_name):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    params = {"q": artist_name, "type": "artist", "limit": 1}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        items = response.json()["artists"]["items"]
        if items:
            return items[0]["id"]
    return None

def get_artist_genres(spotify_id):
    url = f"https://api.spotify.com/v1/artists/{spotify_id}"
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("genres", [])
    return []

# === ENRICHISSEMENT DES GENRES ===
@st.cache_data
def enrich_artists_with_genres(artists_df):
    genres_list = []
    null_count = 0

    for name in artists_df["name"]:
        spotify_id = get_spotify_artist_id(name)
        if spotify_id:
            genres = get_artist_genres(spotify_id)
        else:
            genres = []
            null_count += 1

        genres_list.append(", ".join(genres))
        time.sleep(0.2)  # pour éviter d'être bloqué par l'API

    artists_df["genres"] = genres_list

    # Vérification qualité des genres extraits
    total = len(artists_df)
    empty_ratio = null_count / total
    if empty_ratio > 0.3:
        st.warning(f"⚠️ Attention : {null_count}/{total} artistes sans genre trouvé ({empty_ratio:.0%})")
    else:
        st.success(f"✅ Genres extraits avec succès pour {total - null_count}/{total} artistes")

    return artists_df

# === ENRICHISSEMENT EN TEMPS RÉEL ===
with st.spinner("🔍 Enrichissement des artistes avec leurs genres Spotify..."):
    artists = enrich_artists_with_genres(artists)

# === INTERFACE : SÉLECTION D'UTILISATEUR ===
user_ids = user_artists["userID"].unique()
user_id = st.selectbox("👤 Sélectionne ton ID utilisateur :", user_ids)

# === ARTISTES LES PLUS ÉCOUTÉS ===
st.subheader("🎵 Tes artistes les plus écoutés :")
user_data = user_artists[user_artists["userID"] == user_id]
top_user_artists = user_data.sort_values(by="weight", ascending=False).head(10)
top_user_artists = top_user_artists.merge(artists, left_on="artistID", right_on="id")

if not top_user_artists.empty:
    for _, row in top_user_artists.iterrows():
        st.write(f"- {row['name']} (poids : {row['weight']}) — *Genres:* {row['genres']}")
else:
    st.info("Aucune donnée disponible pour cet utilisateur.")

# === ARTISTES POPULAIRES GLOBALEMENT ===
st.subheader("🌍 Recommandations : Artistes populaires globalement")
global_popularity = (
    user_artists.groupby("artistID")["weight"]
    .sum()
    .reset_index()
    .sort_values(by="weight", ascending=False)
    .head(10)
)
top_global_artists = global_popularity.merge(artists, left_on="artistID", right_on="id")

for _, row in top_global_artists.iterrows():
    st.write(f"- {row['name']} (popularité : {row['weight']}) — *Genres:* {row['genres']}")
