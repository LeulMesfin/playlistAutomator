# final spotify project
from requests import post, get
import os
import requests
import json
import secrets
import string
import webbrowser
from urllib.parse import urlparse, parse_qs
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl
import re
from dotenv import load_dotenv

def configure():
    load_dotenv()

# Purpose:
# The purpose of this project is extract all of the songs
# in a user's Liked videos YouTube playlist, and append
# them to a newly created playlist in Spotify.


redirect_uri = 'http://localhost'
state = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
scope = 'user-read-private user-read-email playlist-modify-public playlist-modify-private'
scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

url = f'https://accounts.spotify.com/authorize?response_type=token&client_id={os.getenv(client_id)}&scope={scope}&redirect_uri={redirect_uri}&state={state}'
response = requests.get(url)

# Open the URL in a web browser for the user to grant access
webbrowser.open(url)

# Wait for user interaction and capture the redirected URL
redirected_url = input("Enter the final URL after granting access: ")

parsed_url = urlparse(redirected_url)
query_params = parse_qs(parsed_url.fragment)

# Extract the values from the query parameters
access_token = query_params.get('access_token', [''])[0]
token_type = query_params.get('token_type', [''])[0]
expires_in = query_params.get('expires_in', [''])[0]
state = query_params.get('state', [''])[0]

# Authorization header
def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

# YouTube client
def get_youtube_client():
    # Copied from YouTube Data API
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "client_secret_CLIENTID.json"

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    
    credentials = flow.run_local_server()


    youtube_client = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    return youtube_client 

# Purpose:
# The purpose of this function is to create
# a playlist in a user's Spotify account.
# This function does this by sending a POST
# request to the Spotify Web API. 

def create_playlist():
    data = {
        "name": "Liked YouTube Videos",
        "description": "A carefully curated playlist of songs Leul enjoys",
        "public": False
    }

    # endpoint = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    endpoint = "https://api.spotify.com/v1/me/playlists"
    headers = get_auth_header(access_token)

    response = post(endpoint, headers=headers, json=data)
    json_resp = response.json()

    # Playlist json
    return json_resp['id']

# Purpose:
# The purpose of this function is to get 
# and return a song URI. Meaning it locates the song name in Spotify and returns the song URI.
# This function takes in a song name and artist name. 
# This function works by sending a GET request
# to the Spotify Web API. 

def get_song_uri(song_name, song_artist):
    endpoint = f"https://api.spotify.com/v1/search?q=remaster%2520track%3A{song_name}artist%3A{song_artist}&type=track&market=US&offset=0&limit-20"
    headers = get_auth_header(access_token)

    # A GET request to the API
    response = requests.get(endpoint, headers=headers)
    songs = json.loads(response.content)["tracks"]["items"]

    # only use first song
    uri = songs[0]["uri"]
   
    return uri

# Purpose:
# The purpose of this function is to 
# add a collection of songs to a desired
# Spotify playlist. This works via a 
# POST request to the Spotify Web API.
# This function takes in a playlist id 
# and a collection of songs.

def add_songs(playlist_id, songs):
    # Collect all of the uris
    # songs.item() is a tuple
    uri = []

    for info in songs.items():
        uri.append(info[1]["spotify_uri"])

    data = {
        "uris": uri,
        "position": 0
    }
    
    endpoint = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = get_auth_header(access_token)

    response = post(endpoint, headers=headers, json=data)
    

# Purpose:
# The purpose of this function is to send a 
# GET request to the YouTube Web API and obtain
# a user's liked videos(music). This function then stores
# songs into a dictionary, with its important information.
# This function takes in a YouTube Client and a dictionary.

def get_liked_videos(youtube_client, all_song_info):
    request = youtube_client.videos().list(
        part="snippet,contentDetails,statistics",
        myRating="like"
    )
    response = request.execute()

    for item in response["items"]:
        video_title = item["snippet"]["title"]
        youtube_url = f"https://www.youtube.com/watch?v={item['id']}"

        # use youtube_dl to collect the song name & artist name    
        ydl_opts = {
            'quiet': True,            # Suppress console output
            'extract_flat': True,     # Extract information without downloading
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl: 
            video = ydl.extract_info(youtube_url, download=False)
        
        if video:
            # use video.get to prevent KeyError
            song_name = video.get("track", "Unknown Track")
            artist = video.get("artist", "Unknown Artist")
            song_uri = get_song_uri(song_name, artist)

            # save all important Song info
            all_song_info[video_title] = {
                "youtube_url": youtube_url,
                "song_name": song_name,
                "artist": artist,
                # add the uri, easy to get song to put into playlist
                "spotify_uri": song_uri
            }

def main():
    configure()
    youtube_client = get_youtube_client()
    all_song_info = {}

    # songs are populated into all_song_info
    get_liked_videos(youtube_client, all_song_info)

    # create playlist and add songs into it
    playlist_id = create_playlist()
    add_songs(playlist_id, all_song_info)
    

if __name__ == "__main__":
    main()