import pandas as pd
import os
import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import subprocess

# === PARAMÈTRES ===
INPUT_PATH = "datasets/artists_gp6.dat"
USER_ARTISTS_PATH = "datasets/user_artists_gp6.dat"

# === INTERFACE STREAMLIT ===
st.set_page_config(page_title="Spotify Recommender", layout="centered")
st.image("images/logo_spotify.png", width=200)
st.title("🎧 Recommandation d'artistes Spotify")

# === BOUTON DE RAFRAÎCHISSEMENT ===
if st.button("🔄 Rafraîchir les données Spotify (noms + genres)"):
    with st.spinner("Extraction des noms Spotify..."):
        subprocess.run(["python3", "name_extraction.py"])
    with st.spinner("Enrichissement des genres..."):
        subprocess.run(["python3", "enrich_genres.py"])
    st.success("✅ Données mises à jour avec succès. Veuillez recharger la page.")
    st.stop()

# === CHARGEMENT DES DONNÉES ===
@st.cache_data
def load_user_data():
    return pd.read_csv(USER_ARTISTS_PATH, sep="\t")

@st.cache_data
def load_artists():
    return pd.read_csv(INPUT_PATH, sep="\t")

user_artists = load_user_data()
artists = load_artists()

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