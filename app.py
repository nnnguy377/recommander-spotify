import streamlit as st
import pandas as pd
import requests
import base64
from io import BytesIO
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import time

# --- Identifiants API Spotify ---
CLIENT_ID = "c284ca8f68794e6f84c8c62f6f26efc0"
CLIENT_SECRET = "1f4917a93a024c9fbab79b3982df6076"

# --- Fonction pour récupérer le token Spotify ---
@st.cache_data(ttl=3600, show_spinner=False)
def get_spotify_token(client_id, client_secret):
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {"Authorization": f"Basic {b64_auth}"}
    data = {"grant_type": "client_credentials"}
    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    return response.json().get("access_token")

# --- Fonction pour récupérer les genres d'un artiste via Spotify ---
@st.cache_data(show_spinner=False)
def get_artist_genres_from_spotify(artist_name, token):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": artist_name, "type": "artist", "limit": 1}
    response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
    if response.status_code != 200:
        return "unknown"
    data = response.json()
    items = data.get("artists", {}).get("items", [])
    if items and "genres" in items[0]:
        return ", ".join(items[0]["genres"]) if items[0]["genres"] else "unknown"
    return "unknown"

# --- Fonction pour récupérer l'image d'un artiste via Spotify ---
@st.cache_data(show_spinner=False)
def get_artist_image_from_spotify(artist_name, token):
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": artist_name, "type": "artist", "limit": 1}
    response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)
    if response.status_code != 200:
        return None
    data = response.json()
    items = data.get("artists", {}).get("items", [])
    if items and items[0].get("images"):
        return items[0]["images"][0]["url"]
    return None

# --- Fonction pour afficher l'image via Spotify uniquement ---
def display_spotify_artist_image(artist_name, token):
    img_url = get_artist_image_from_spotify(artist_name, token)
    if img_url:
        try:
            response = requests.get(img_url)
            response.raise_for_status()
            img = BytesIO(response.content)
            st.image(img, width=150, caption=artist_name)
        except requests.exceptions.RequestException:
            st.markdown(f"### {artist_name} (Image load failed)")
    else:
        st.markdown(f"### {artist_name} (No Image Available)")

# --- UI STYLING + LOGO ---
st.image("images/logo_spotify.png", width=200)

st.markdown("""
<style>
    body { background-color: #121212; color: white; }
    h1, h2, h3, h4, h5, h6 { color: #1DB954 !important; }
    .stApp { background-color: #121212; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1DB954 !important; }
    .stTable { background-color: #181818; color: white; }
    .stButton > button { background-color: #1DB954 !important; color: black !important; border-radius: 8px; }
    .stNumberInput > div > div > input { background-color: #282828; color: white; }
</style>
""", unsafe_allow_html=True)

# --- Obtenir le token Spotify ---
token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)

# --- Chargement des données ---
df_artists = pd.read_csv("datasets/artists_gp6.dat", sep="\t")
df_user_artists = pd.read_csv("datasets/user_artists_gp6.dat", sep="\t")

# --- Extraction des genres si colonne manquante ou vide ---
if "genres" not in df_artists.columns or df_artists["genres"].isnull().all():
    st.warning("🔄 Extraction des genres Spotify en cours...")
    genres_list = []
    progress_bar = st.progress(0)
    for idx, row in df_artists.iterrows():
        genre = get_artist_genres_from_spotify(row["name"], token)
        genres_list.append(genre)
        if idx % 10 == 0:
            progress_bar.progress(min(int(idx / len(df_artists) * 100), 100))
    df_artists["genres"] = genres_list
    df_artists.to_csv("datasets/artists_gp6.dat", sep="\t", index=False)
    progress_bar.empty()

# --- Nettoyage des genres ---
df_artists["genres"] = df_artists["genres"].fillna("").astype(str)
df_artists["genres"] = df_artists["genres"].apply(lambda g: g if g.strip() != "" else "unknown")

# --- Sidebar ---
st.sidebar.title("🎛️ Type de recommandation")
reco_type = st.sidebar.radio("Choisissez le modèle :", ["Content-Based", "Popularity-Based"])

# --- Interface principale ---
st.title("🎵 Music Recommendation App")
user_id = st.number_input("Entrez votre ID utilisateur :", min_value=1, step=1)

if st.button("Voir mes recommandations") and token:

    user_data = df_user_artists[df_user_artists["userID"] == user_id]
    user_artists = user_data.merge(df_artists, left_on="artistID", right_on="id")

    if user_artists.empty:
        st.warning("❌ Aucun artiste trouvé pour cet utilisateur.")
        st.stop()

    st.subheader("🎧 Vos artistes préférés")
    st.table(user_artists[["name", "genres"]].rename(columns={"name": "Artist"}).head(10))

    # --- Content-Based ---
    if reco_type == "Content-Based":
        st.subheader("🎯 Recommandations basées sur les genres Spotify")
        user_profile = " ".join(user_artists["genres"])
        tfidf = TfidfVectorizer()
        tfidf_matrix = tfidf.fit_transform(df_artists["genres"])
        user_vec = tfidf.transform([user_profile])
        similarity = cosine_similarity(user_vec, tfidf_matrix).flatten()
        df_artists["similarity"] = similarity
        known_ids = user_artists["id"].tolist()
        recommendations = df_artists[~df_artists["id"].isin(known_ids)]
        top_recos = recommendations.sort_values(by="similarity", ascending=False).head(10)

        top_artist = top_recos.iloc[0]
        display_spotify_artist_image(top_artist["name"], token)
        st.markdown(f"### {top_artist['name']}")
        st.table(top_recos[["name", "genres", "similarity"]].rename(columns={"name": "Artist"}))

    # --- Popularity-Based ---
    elif reco_type == "Popularity-Based":
        st.subheader("🔥 Recommandations par popularité")
        pop_df = df_user_artists.groupby("artistID")["weight"].sum().reset_index()
        pop_df = pop_df.merge(df_artists, left_on="artistID", right_on="id")
        pop_df = pop_df[~pop_df["artistID"].isin(user_artists["artistID"])]
        top_pop = pop_df.sort_values(by="weight", ascending=False).head(10)

        top_artist = top_pop.iloc[0]
        display_spotify_artist_image(top_artist["name"], token)
        st.markdown(f"### {top_artist['name']}")
        st.table(top_pop[["name", "genres", "weight"]].rename(columns={"name": "Artist", "weight": "Popularity Score"}))

    # --- Feedback utilisateur ---
    st.subheader("🗳️ Avez-vous aimé ces recommandations ?")
    feedback = st.radio("Votre avis :", ["👍 Oui", "👎 Non"])
    if feedback == "👍 Oui":
        st.success("Merci pour votre retour positif ! 😊")
    else:
        st.info("Merci pour le retour ! On essaiera d'améliorer les suggestions.")