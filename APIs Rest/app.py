from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import json
import requests

app = FastAPI()

# Base de datos simulada
usuarios = []

# Credenciales de Spotify
CLIENT_ID = "b226a6b42b77473683f5724d1965e463"
REDIRECT_URI = "http://localhost:8000/callback"
CLIENT_SECRET = "c36a5d3e9f7c454c99f0b85d97ff66b1"

# Variables globales para almacenar el token
spotify_access_token = None
spotify_refresh_token = None

#------------------------------------------------------------------------------------------------------
# Funciones
#------------------------------------------------------------------------------------------------------
# Función de autenticación: Obtener el Access Token
def get_access_token(code: str):
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",     # Tipo de flujo OAuth
        "code": code,                           # Authorization Code recibido
        "redirect_uri": REDIRECT_URI,           
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code == 200:
        return response.json()                  # Contendrá access_token y refresh_token
    else:
        raise Exception("Error al obtener el Access Token")

# Función para renovar el Access Token
def refresh_access_token(refresh_token: str):
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        return response.json()                  # Nuevo Access Token
    else:
        raise Exception("Error renovando el Access Token")

# Función para obtener los artistas más escuchados
def get_top_artists(access_token: str):
    url = "https://api.spotify.com/v1/me/top/artists"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error al obtener los artistas más escuchados: {response.status_code}")

# Función para obtener las canciones favoritas (top tracks)
def get_top_tracks(access_token: str):
    url = "https://api.spotify.com/v1/me/top/tracks"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Error al obtener las canciones más escuchadas: {response.status_code}")

# Función para obtener la información de un artista
def get_artist_info(artist_id: str, access_token: str):
    url = f"https://api.spotify.com/v1/artists/{artist_id}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception("Error al obtener la información del artista")

# Modelo de Usuario
class Usuario(BaseModel):
    nombre: str
    email: str
    preferences: list[str] = []             # Lista de preferencias musicales

#------------------------------------------------------------------------------------------------------
# Endpoints
#------------------------------------------------------------------------------------------------------
# Ruta 1: Login - Redirige al usuario a Spotify para autorización
@app.get("/login")
async def login():
    auth_url = (
        "https://accounts.spotify.com/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        "&scope=user-library-read user-top-read playlist-read-private"
    )
    return RedirectResponse(auth_url)

# Ruta 2: Callback - Recibe el código de Spotify y almacena el token
@app.get("/callback")
async def callback(code: str):
    global spotify_access_token, spotify_refresh_token
    try:
        token_data = get_access_token(code)
        spotify_access_token = token_data.get("access_token")
        spotify_refresh_token = token_data.get("refresh_token")
        return {"message": "Token obtenido y almacenado correctamente", "token_data": token_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Ruta 3: Crear un nuevo usuario (POST /api/users)
@app.post('/api/users', status_code=201)
def create_user(usuario: Usuario):
    if any(u['email'] == usuario.email for u in usuarios):
        raise HTTPException(status_code=400, detail="Este email ya existe")
    new_user = {
        "id": len(usuarios) + 1,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "preferences": usuario.preferences
    }
    usuarios.append(new_user)
    return {"message": "Usuario creado", "usuario": new_user}

# Ruta 4: Obtener los datos de un usuario (GET /api/users/{user_id})
@app.get('/api/users/{user_id}')
def get_user(user_id: int):
    user = next((u for u in usuarios if u['id'] == user_id), None)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"usuario": user}

# Ruta 5: Actualizar los datos de un usuario (PUT /api/users/{user_id})
@app.put('/api/users/{user_id}')
def update_user(user_id: int, usuario: Usuario):
    user = next((u for u in usuarios if u['id'] == user_id), None)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user['nombre'] = usuario.nombre
    user['email'] = usuario.email
    user['preferences'] = usuario.preferences
    return {"message": "Usuario actualizado", "usuario": user}

# Ruta 6: Eliminar un usuario (DELETE /api/users/{user_id})
@app.delete('/api/users/{user_id}')
def delete_user(user_id: int):
    user = next((u for u in usuarios if u['id'] == user_id), None)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    usuarios.remove(user)
    return {"message": "Usuario eliminado", "usuario": user}

# Ruta 7: Agregar una preferencia musical (POST /api/users/{user_id}/preferences)
@app.post('/api/users/{user_id}/preferences')
def add_preference(user_id: int, preference: str):
    user = next((u for u in usuarios if u['id'] == user_id), None)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if preference not in user['preferences']:
        user['preferences'].append(preference)
    return {"message": "Preferencia añadida", "usuario": user}

# Ruta 8: Eliminar una preferencia musical (DELETE /api/users/{user_id}/preferences)
@app.delete('/api/users/{user_id}/preferences')
def remove_preference(user_id: int, preference: str):
    user = next((u for u in usuarios if u['id'] == user_id), None)
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if preference in user['preferences']:
        user['preferences'].remove(preference)
    return {"message": "Preferencia eliminada", "usuario": user}

# Ruta 9: Obtener artistas y canciones más escuchadas (/me/top)
@app.get("/me/top")
async def get_user_top_data():
    global spotify_access_token
    if not spotify_access_token:
        raise HTTPException(status_code=400, detail="No se encontró Access Token. Inicia sesión en /login y autoriza la app.")
    try:
        artists_data = get_top_artists(spotify_access_token)
        tracks_data = get_top_tracks(spotify_access_token)
        return {"top_artists": artists_data, "top_tracks": tracks_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Ruta 10: Obtener Información de un Artista (/artist/{artist_id})
@app.get("/artist/{artist_id}")
async def get_artist(artist_id: str):
    global spotify_access_token
    if not spotify_access_token:
        raise HTTPException(status_code=400, detail="No se encontró Access Token. Inicia sesión en /login y autoriza la app.")
    try:
        artist_data = get_artist_info(artist_id, spotify_access_token)
        return artist_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
