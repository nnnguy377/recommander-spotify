import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Fonction pour afficher l'image à partir d'une URL
def display_artist_image(url, artist_name):
    if pd.notna(url) and url.startswith("http"):
        try:
            response = requests.get(url)
            response.raise_for_status()  # Vérifie que l'URL est valide
            img = BytesIO(response.content)
            st.image(img, width=150)
        except requests.exceptions.RequestException:
            st.markdown(f"### {artist_name} (No Image Available)")
    else:
        st.markdown(f"### {artist_name} (No Image Available)")

# Afficher le logo Spotify mis à jour en haut de la page
st.image("logo_spotify.png", width=200)

# Appliquer un style personnalisé en accord avec la charte graphique de Spotify
st.markdown(
    """
    <style>
        body {
            background-color: #000000; /* Fond noir pur */
            color: #FFFFFF;
        }
        .stButton>button {
            background-color: #FFFFFF !important; /* Bouton blanc même lorsqu'on clique dessus */
            color: #000000 !important; /* Texte noir pour contraste */
            border-radius: 25px;
            border: none;
            font-size: 16px;
            padding: 10px;
        }
        .stNumberInput>div>div>input {
            background-color: #282828; /* Gris foncé Spotify */
            color: white;
            border-radius: 5px;
            border: 1px solid #535353;
        }
        .stTable { 
            background-color: #181818; /* Table sur fond gris foncé */
            color: white;
            border-radius: 10px;
        }
        .stTextInput>div>div>input {
            background-color: #282828;
            color: white;
            border: 1px solid #535353;
        }
        h1, h2, h3 {
            color: #1DB954; /* Titres en vert Spotify */
        }
        table { 
            border-collapse: collapse; 
            border: none; /* Supprime les bordures des tableaux */
        }
        thead {
            display: table-header-group; /* Réaffiche les en-têtes des tableaux */
            font-weight: bold;
            color: #FFFFFF; /* Couleur blanche pour le texte */
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Chargement des données
df_user_artists = pd.read_csv("user_artists_gp6.dat", sep="\t")
df_artists = pd.read_csv("artists_gp6.dat", sep="\t")

# Interface utilisateur
st.title("🎵 Music Recommendation")
user_id = st.number_input("Enter your user ID:", min_value=1, step=1)

if st.button("See my recommendations"):
    user_data = df_user_artists[df_user_artists["userID"] == user_id]
    
    st.subheader("🎧 Your Favorite Artists")
    user_artists = user_data.merge(df_artists, left_on="artistID", right_on="id")[["id", "name", "weight", "pictureURL"]]
    user_artists = user_artists.sort_values(by="weight", ascending=False).head(10)
    user_artists.reset_index(drop=True, inplace=True)  # Supprime l'ancien index
    user_artists.index = user_artists.index + 1  # Ajoute le classement de 1 à 10
    user_artists = user_artists.rename(columns={"name": "Artist", "weight": "Score"})  # Renommer les colonnes
    
    # Afficher l'image du premier artiste favori
    top_fav_artist = user_artists.iloc[0]
    display_artist_image(top_fav_artist["pictureURL"], top_fav_artist["Artist"])
    
    st.markdown(f"### {top_fav_artist['Artist']}")
    
    st.table(user_artists[["Artist", "Score"]])
    
    st.subheader("🔥 Recommendations")
    similar_users = df_user_artists[df_user_artists["artistID"].isin(user_data["artistID"]) & (df_user_artists["userID"] != user_id)]["userID"].unique()
    
    recommended_artists = df_user_artists[df_user_artists["userID"].isin(similar_users)]
    recommended_artists = recommended_artists.groupby("artistID")["weight"].sum().reset_index()
    recommended_artists = recommended_artists.sort_values(by="weight", ascending=False)
    recommended_artists = recommended_artists.merge(df_artists, left_on="artistID", right_on="id")[["id", "name", "weight", "pictureURL"]]
    
    # Supprimer les artistes déjà présents dans "Your Favorite Artists"
    recommended_artists = recommended_artists[~recommended_artists["name"].isin(user_artists["Artist"])].head(10)
    
    recommended_artists.reset_index(drop=True, inplace=True)  # Supprime l'ancien index
    recommended_artists.index = recommended_artists.index + 1  # Ajoute le classement de 1 à 10
    recommended_artists = recommended_artists.rename(columns={"name": "Artist", "weight": "Score"})
    
    # Afficher l'image du premier artiste recommandé
    top_recommended_artist = recommended_artists.iloc[0]
    display_artist_image(top_recommended_artist["pictureURL"], top_recommended_artist["Artist"])
    
    st.markdown(f"### {top_recommended_artist['Artist']}")
    
    st.table(recommended_artists[["Artist", "Score"]])