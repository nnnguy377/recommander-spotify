import pandas as pd
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.model_selection import train_test_split

# 1️⃣ Charger les données
user_artists_file = "datasets/user_artists_gp6.dat"
artists_file = "datasets/artists_gp6.dat"

# Charger les fichiers avec les noms échangés
artists_df = pd.read_csv(user_artists_file, sep="\t")  # Données utilisateurs
df = pd.read_csv(artists_file, sep="\t")               # Données artistes

# 2️⃣ Construire la matrice utilisateur-artiste
user_artist_matrix = artists_df.pivot(index="userID", columns="artistID", values="weight").fillna(0)

# Diviser les données en ensembles d'entraînement et de test
train_data, test_data = train_test_split(user_artist_matrix, test_size=0.2, random_state=42)

# Filtrer l'ensemble de test pour ne garder que les utilisateurs présents dans l'ensemble d'entraînement
test_data = test_data.loc[test_data.index.isin(train_data.index)]

# 3️⃣ Factorisation avec TruncatedSVD sur les données d'entraînement
svd = TruncatedSVD(n_components=20, random_state=42)
user_factors = svd.fit_transform(train_data)
artist_factors = svd.components_

# 4️⃣ Fonction de recommandation
def recommend_artists(user_id, df, n=10):
    if user_id not in train_data.index:
        print(f"L'utilisateur {user_id} n'existe pas dans les données.")
        return []

    user_index = train_data.index.get_loc(user_id)
    scores = np.dot(user_factors[user_index], artist_factors)

    listened_artists = set(train_data.loc[user_id][train_data.loc[user_id] > 0].index)
    recommendations = [(artist_id, scores[i]) for i, artist_id in enumerate(train_data.columns) if artist_id not in listened_artists]

    top_recommendations = sorted(recommendations, key=lambda x: x[1], reverse=True)[:n]

    # Vérifiez que les artistes recommandés existent dans le DataFrame des artistes
    artist_ids = [artist_id for artist_id, _ in top_recommendations]
    artist_names = df[df["id"].isin(artist_ids)].set_index("id")["name"]

    return [(artist_names.get(artist_id, "Inconnu"), score)
            for artist_id, score in top_recommendations]

# 5️⃣ Fonction pour évaluer les recommandations
def evaluate_recommendations(test_data, n=10):
    precisions = []
    recalls = []
    f1_scores = []

    for user_id in test_data.index:
        true_artists = set(test_data.loc[user_id][test_data.loc[user_id] > 0].index)
        recommended_artists = set([artist_id for artist_id, _ in recommend_artists(user_id, df, n)])

        if not recommended_artists:
            continue  # Ignorer les utilisateurs sans recommandations

        true_positives = true_artists.intersection(recommended_artists)
        precision = len(true_positives) / len(recommended_artists) if recommended_artists else 0
        recall = len(true_positives) / len(true_artists) if true_artists else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        precisions.append(precision)
        recalls.append(recall)
        f1_scores.append(f1)

    # Vérifier si les listes sont vides avant de calculer les moyennes
    if precisions:
        precision_mean = np.mean(precisions)
    else:
        precision_mean = 0

    if recalls:
        recall_mean = np.mean(recalls)
    else:
        recall_mean = 0

    if f1_scores:
        f1_mean = np.mean(f1_scores)
    else:
        f1_mean = 0

    return precision_mean, recall_mean, f1_mean

# 6️⃣ Évaluer les recommandations
precision, recall, f1 = evaluate_recommendations(test_data, n=10)
print(f"Précision: {precision:.2f}")
print(f"Rappel: {recall:.2f}")
print(f"F1-Score: {f1:.2f}")

# 7️⃣ Tester avec un utilisateur donné
user_id = 1288
top_artists = recommend_artists(user_id, df, n=10)

print(f"Top 10 artistes recommandés pour l'utilisateur {user_id}:")
for artist, score in top_artists:
    print(f"- {artist} (Score: {score:.2f})")

