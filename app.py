import pandas as pd
import requests
import base64
import time
import os
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# === PARAMÈTRES ===
CLIENT_ID = "c284ca8f68794e6f84c8c62f6f26efc0"
CLIENT_SECRET = "1f4917a93a024c9fbab79b3982df6076"
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
        st.error(f"❌ Fichier introuvable : {filepath}")
        return pd.DataFrame()

    df = pd.read_csv(filepath, sep="\t")
    genres_list = []
    null_count = 0

    for name in df["name"]:
        artist_id = get_spotify_artist_id(name, token)
        if artist_id:
            genres = get_artist_genres(artist_id, token)
        else:
            genres = []
            null_count += 1
        genres_list.append(", ".join(genres))
        time.sleep(SLEEP_TIME)

    df["genres"] = genres_list
    df.to_csv(filepath, sep="\t", index=False)

    st.success(f"✅ Genres extraits pour {len(df) - null_count}/{len(df)} artistes")
    return df

# === INTERFACE STREAMLIT ===
st.set_page_config(page_title="Spotify Recommender", layout="centered")
st.image("images/logo_spotify.png", width=200)
st.title("🎧 Recommandation d'artistes Spotify")

# === CHARGEMENT DES DONNÉES ===
@st.cache_data
def load_user_data():
    return pd.read_csv(USER_ARTISTS_PATH, sep="\t")

@st.cache_data
def load_artists():
    return pd.read_csv(INPUT_PATH, sep="\t")

user_artists = load_user_data()
artists = load_artists()

# === ENRICHISSEMENT AUTOMATIQUE SI GENRES ABSENTS ===
if "genres" not in artists.columns or artists["genres"].isnull().all():
    st.warning("Les genres sont manquants, enrichissement en cours via l'API Spotify...")
    token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)
    if token:
        artists = enrich_artists(INPUT_PATH, token)
    else:
        st.error("Impossible de récupérer le token Spotify. Vérifiez vos identifiants.")
        st.stop()

# === INTERFACE UTILISATEUR ===
st.sidebar.header("🎚️ Options de recommandation")
user_ids = user_artists["userID"].unique()
user_id = st.sidebar.selectbox("Sélectionnez votre ID utilisateur :", sorted(user_ids))
mode = st.sidebar.radio("Méthode de recommandation :", ["Popularité globale", "Basée sur le contenu"])

# === ARTISTES LES PLUS ÉCOUTÉS PAR L'UTILISATEUR ===
st.subheader("🎵 Tes artistes les plus écoutés :")
user_data = user_artists[user_artists["userID"] == user_id]
top_user_artists = user_data.sort_values(by="weight", ascending=False).head(10)
top_user_artists = top_user_artists.merge(artists, left_on="artistID", right_on="id")

if not top_user_artists.empty:
    for _, row in top_user_artists.iterrows():
        st.write(f"- {row['name']} (poids : {row['weight']}) — *Genres:* {row.get('genres', 'N/A')}")
else:
    st.info("Aucune donnée disponible pour cet utilisateur.")

# === RECOMMANDATION PAR POPULARITÉ ===
def recommend_by_popularity():
    global_popularity = (
        user_artists.groupby("artistID")["weight"]
        .sum()
        .reset_index()
        .sort_values(by="weight", ascending=False)
    )
    top_artists = global_popularity.merge(artists, left_on="artistID", right_on="id")
    return top_artists[~top_artists["artistID"].isin(top_user_artists["artistID"])]

# === RECOMMANDATION BASÉE SUR LE CONTENU ===
def recommend_by_content():
    if "genres" not in artists.columns:
        st.warning("🚫 Aucune colonne 'genres' détectée dans les données artistes.")
        return pd.DataFrame()

    merged = user_data.merge(artists, left_on="artistID", right_on="id")
    merged = merged[merged["genres"].notna() & (merged["genres"] != "")]

    if merged.empty:
        return pd.DataFrame()

    user_profile = merged.sort_values(by="weight", ascending=False).head(5)
    user_genre_text = " ".join(user_profile["genres"].fillna(""))

    tfidf = TfidfVectorizer()
    tfidf_matrix = tfidf.fit_transform(artists["genres"].fillna(""))
    user_vec = tfidf.transform([user_genre_text])

    cosine_sim = cosine_similarity(user_vec, tfidf_matrix).flatten()
    artists["similarity"] = cosine_sim
    recommendations = artists[~artists["id"].isin(user_profile["id"])]
    recommendations = recommendations.sort_values(by="similarity", ascending=False)
    return recommendations

# === AFFICHAGE DES RECOMMANDATIONS ===
st.subheader("🌟 Recommandations :")
if mode == "Popularité globale":
    reco = recommend_by_popularity().head(10)
    for _, row in reco.iterrows():
        st.write(f"- {row['name']} (popularité : {row['weight']}) — *Genres:* {row.get('genres', 'N/A')}")
elif mode == "Basée sur le contenu":
    reco = recommend_by_content().head(10)
    if reco.empty:
        st.warning("Pas assez d'information de genres pour proposer une recommandation.")
    else:
        for _, row in reco.iterrows():
            st.write(f"- {row['name']} — *Genres:* {row.get('genres', 'N/A')} (similarité: {row['similarity']:.2f})")
