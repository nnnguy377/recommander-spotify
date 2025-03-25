import requests
import base64

# 🔐 REMPLACE ICI
CLIENT_ID = "5887ae6066b5474193c81da5736f9e0a"
CLIENT_SECRET = "083cf1c69bb74fcb90157eaba59b7a86"

def get_token(client_id, client_secret):
    print("🔐 Récupération du token...")
    url = "https://accounts.spotify.com/api/token"
    auth_str = f"{client_id}:{client_secret}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, headers=headers, data=data)
    if r.status_code == 200:
        return r.json()["access_token"]
    print("❌ Échec token:", r.text)
    return None

def search_artist(name, token):
    print(f"🔍 Recherche de l'artiste: {name}")
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": name, "type": "artist", "limit": 1}
    r = requests.get(url, headers=headers, params=params)
    if r.status_code != 200:
        print("❌ Erreur API:", r.text)
        return None
    data = r.json()
    items = data.get("artists", {}).get("items", [])
    if not items:
        print("❌ Aucun artiste trouvé")
        return None
    artist = items[0]
    print("✅ Artiste trouvé:", artist["name"], "| ID:", artist["id"])
    return artist["id"]

def get_genres(artist_id, token):
    print(f"🎵 Récupération des genres pour l'ID: {artist_id}")
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        genres = r.json().get("genres", [])
        print("✅ Genres:", genres)
    else:
        print("❌ Erreur récupération genres:", r.text)

# === TEST ===
if __name__ == "__main__":
    token = get_token(CLIENT_ID, CLIENT_SECRET)
    if not token:
        exit()

    artist_id = search_artist("Daft Punk", token)
    if artist_id:
        get_genres(artist_id, token)
