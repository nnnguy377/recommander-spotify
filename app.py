import pandas as pd
import streamlit as st

# Titre et logo
st.set_page_config(page_title="Recommandations Spotify", layout="centered")
st.image("images/logo_spotify.png", width=200)
st.title("🎧 Recommandation d'artistes Spotify")

# Charger les fichiers
@st.cache_data
def load_data():
    artists = pd.read_csv("datasets/artists_gp6.dat", sep="\t")
    user_artists = pd.read_csv("datasets/user_artists_gp6.dat", sep="\t")
    return artists, user_artists

artists, user_artists = load_data()

# Sélection utilisateur
user_ids = user_artists["userID"].unique()
user_id = st.selectbox("Sélectionne ton ID utilisateur :", user_ids)

# Recommandations simples : top artistes écoutés par cet utilisateur
user_data = user_artists[user_artists["userID"] == user_id]
top_artists = user_data.sort_values(by="weight", ascending=False).head(10)
top_artists = top_artists.merge(artists, left_on="artistID", right_on="id")

st.subheader("🎵 Tes artistes les plus écoutés :")
for i, row in top_artists.iterrows():
    st.write(f"{row['name']} (poids : {row['weight']})")
