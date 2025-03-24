import streamlit as st
import pandas as pd
import requests
import base64
from io import BytesIO

# --- Identifiants API Spotify ---
CLIENT_ID = "c284ca8f68794e6f84c8c62f6f26efc0"
CLIENT_SECRET = "1f4917a93a024c9fbab79b3982df6076"

# --- Fonction pour récupérer le token Spotify ---
@st.cache_data(show_spinner=False)
def get_spotify_token(client_id, client_secret):
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_auth}"
    }
    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    if response.status_code == 200:
        return response.json()["access_token"]
    else:
        st.error("❌ Impossible de récupérer le token Spotify.")
        return None

# --- Fonction pour récupérer l'image d'un artiste via Spotify ---
@st.cache_data(show_spinner=False)
def get_artist_image_from_spotify(artist_name, token):
    headers = {
        "Authorization": f"Bearer {token}"
    }
    params = {
        "q": artist_name,
        "type": "artist",
        "limit": 1
    }

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
    body { background-color: #000000; color: #FFFFFF; }
    h1, h2, h3 { color: #1DB954 !important; }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #1DB954 !important; }
    .stButton>button {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-radius: 25px;
        border: none;
        font-size: 16px;
        padding: 10px;
    }
    .stNumberInput>div>div>input {
        background-color: #282828;
        color: white;
        border-radius: 5px;
        border: 1px solid #535353;
    }
    .stTable { background-color: #181818; color: white; border-radius: 10px; }
    .stTextInput>div>div>input {
        background-color: #282828;
        color: white;
        border: 1px solid #535353;
    }
    table { border-collapse: collapse; border: none; }
    thead {
        display: table-header-group;
        font-weight: bold;
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)

# --- Chargement des données ---
df_user_artists = pd.read_csv("datasets/user_artists_gp6.dat", sep="\t")
df_artists = pd.read_csv("datasets/artists_gp6.dat", sep="\t")

# --- Obtenir le token ---
token = get_spotify_token(CLIENT_ID, CLIENT_SECRET)

# --- Interface principale ---
st.title("🎵 Music Recommendation")
user_id = st.number_input("Enter your user ID:", min_value=1, step=1)

if st.button("See my recommendations") and token:
    user_data = df_user_artists[df_user_artists["userID"] == user_id]

    st.subheader("🎧 Your Favorite Artists")
    user_artists = user_data.merge(df_artists, left_on="artistID", right_on="id")[["id", "name", "weight"]]
    user_artists = user_artists.sort_values(by="weight", ascending=False).head(10)
    user_artists.reset_index(drop=True, inplace=True)
    user_artists.index = user_artists.index + 1
    user_artists = user_artists.rename(columns={"name": "Artist", "weight": "Score"})

    # Afficher uniquement l'image du premier artiste favori via Spotify
    top_fav_artist = user_artists.iloc[0]
    display_spotify_artist_image(top_fav_artist["Artist"], token)
    st.markdown(f"### {top_fav_artist['Artist']}")
    st.table(user_artists[["Artist", "Score"]])

    st.subheader("🔥 Recommendations")
    similar_users = df_user_artists[
        (df_user_artists["artistID"].isin(user_data["artistID"])) &
        (df_user_artists["userID"] != user_id)
    ]["userID"].unique()

    recommended_artists = df_user_artists[df_user_artists["userID"].isin(similar_users)]
    recommended_artists = recommended_artists.groupby("artistID")["weight"].sum().reset_index()
    recommended_artists = recommended_artists.sort_values(by="weight", ascending=False)
    recommended_artists = recommended_artists.merge(df_artists, left_on="artistID", right_on="id")[["id", "name", "weight"]]

    recommended_artists = recommended_artists[~recommended_artists["name"].isin(user_artists["Artist"])].head(10)
    recommended_artists.reset_index(drop=True, inplace=True)
    recommended_artists.index = recommended_artists.index + 1
    recommended_artists = recommended_artists.rename(columns={"name": "Artist", "weight": "Score"})

    # Afficher uniquement l'image du premier artiste recommandé via Spotify
    top_recommended_artist = recommended_artists.iloc[0]
    display_spotify_artist_image(top_recommended_artist["Artist"], token)
    st.markdown(f"### {top_recommended_artist['Artist']}")
    st.table(recommended_artists[["Artist", "Score"]])