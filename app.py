import pandas as pd
import streamlit as st

# Configuration de la page
st.set_page_config(page_title="Recommandations Spotify", layout="centered")

# Affichage du logo
st.image("images/logo_spotify.png", width=200)
st.title("🎧 Recommandation d'artistes Spotify")

# Chargement des données
@st.cache_data
def load_data():
    artists = pd.read_csv("datasets/artists_gp6.dat", sep="\t")
    user_artists = pd.read_csv("datasets/user_artists_gp6.dat", sep="\t")
    return artists, user_artists

artists, user_artists = load_data()

# Sélection de l'utilisateur
user_ids = user_artists["userID"].unique()
user_id = st.selectbox("Sélectionne ton ID utilisateur :", user_ids)

# === 🎵 RUBRIQUE : Artistes les plus écoutés par l'utilisateur ===
st.subheader("🎵 Tes artistes les plus écoutés :")

user_data = user_artists[user_artists["userID"] == user_id]
top_user_artists = user_data.sort_values(by="weight", ascending=False).head(10)
top_user_artists = top_user_artists.merge(artists, left_on="artistID", right_on="id")

if not top_user_artists.empty:
    for i, row in top_user_artists.iterrows():
        st.write(f"- {row['name']} (poids : {row['weight']})")
else:
    st.write("Aucune donnée disponible pour cet utilisateur.")

# === 🌍 RUBRIQUE : Recommandations (popularité globale) ===
st.subheader("🌍 Recommandations : Artistes populaires globalement")

# Calcul des artistes les plus populaires globalement (somme des poids)
global_popularity = (
    user_artists.groupby("artistID")["weight"]
    .sum()
    .reset_index()
    .sort_values(by="weight", ascending=False)
    .head(10)
)

# Jointure avec les noms d'artistes
top_global_artists = global_popularity.merge(artists, left_on="artistID", right_on="id")

for i, row in top_global_artists.iterrows():
    st.write(f"- {row['name']} (popularité : {row['weight']})")
