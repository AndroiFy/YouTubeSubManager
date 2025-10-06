import os
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from src.config import (
    T, E, SCOPES, API_SERVICE_NAME, API_VERSION, CLIENT_SECRETS_FILE,
    normalize_language_code, validate_language_code
)
from src.cache import generate_cache_key, get_from_cache, save_to_cache
from src.quota import increment_quota

def get_authenticated_service(channel_nickname):
    token_file = f"token_{channel_nickname}.json"
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"{T.INFO}{E.INFO} Access token for '{channel_nickname}' expired. Refreshing automatically...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"{T.WARN}{E.WARN} Could not refresh token: {e}. Please re-authenticate.")
                os.remove(token_file); creds = None
        if not creds:
            print(f"{T.WARN}{E.KEY} No valid token for '{channel_nickname}'. Please authenticate via the browser.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            print(f"{T.OK}{E.SUCCESS} Authentication successful. Token saved to '{token_file}'.")
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def get_channel_videos(youtube, channel_id):
    """Retrieves all videos for a channel, using a cache to avoid redundant API calls."""
    cache_key = generate_cache_key("get_channel_videos", channel_id=channel_id)
    cached_videos = get_from_cache(cache_key)
    if cached_videos:
        print(f"{T.INFO}{E.INFO} Found channel videos in cache. Skipping API call.")
        return cached_videos

    print(f"{T.INFO}{E.DOWNLOAD} Fetching channel videos from YouTube API...")
    video_ids = []
    try:
        res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
        increment_quota('channels.list')
        playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        next_page_token = None
        while True:
            res = youtube.playlistItems().list(playlistId=playlist_id, part='snippet', maxResults=50, pageToken=next_page_token).execute()
            increment_quota('playlistItems.list')
            for item in res['items']:
                video_ids.append({'id': item['snippet']['resourceId']['videoId'], 'title': item['snippet']['title']})
            next_page_token = res.get('nextPageToken')
            if not next_page_token: break

        print(f"{T.OK}Found {len(video_ids)} videos in the channel.")
        save_to_cache(cache_key, video_ids)
        return video_ids
    except HttpError as e:
        print(f"{T.FAIL}{E.FAIL} An HTTP error occurred: {e}")
        return []

def list_captions(youtube, video_id):
    """
    Lists all captions for a video, using a cache to avoid redundant API calls.
    The caller is responsible for handling HttpError.
    """
    cache_key = generate_cache_key("list_captions", video_id=video_id)
    cached_captions = get_from_cache(cache_key)
    if cached_captions is not None:
        return cached_captions

    response = youtube.captions().list(part="snippet", videoId=video_id).execute()
    increment_quota('captions.list')
    save_to_cache(cache_key, response)
    return response

def upload_caption(youtube, video_id, language, file_path):
    """Uploads a caption and returns the API response."""
    normalized_lang = normalize_language_code(language)
    if not validate_language_code(normalized_lang):
        print(f"{T.WARN}{E.WARN} Warning: '{normalized_lang}' may not be a valid YouTube language code.")

    print(f"{T.INFO}  {E.ROCKET} Uploading '{normalized_lang}' caption from '{file_path}'...")
    body = {'snippet': {'videoId': video_id, 'language': normalized_lang, 'isDraft': False}}
    media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    response = youtube.captions().insert(part="snippet", body=body, media_body=media_body).execute()
    increment_quota('captions.insert')
    print(f"{T.OK}    {E.SUCCESS} Upload successful! Caption ID: {response['id']}.")
    return response

def update_caption(youtube, video_id, language, file_path, caption_id=None):
    """Updates a caption and returns the API response."""
    normalized_lang = normalize_language_code(language)
    print(f"{T.INFO}  {E.PROCESS} Updating '{normalized_lang}' caption for video {video_id}...")

    is_valid_caption_id = pd.notna(caption_id) and str(caption_id).strip()

    if is_valid_caption_id:
        str_caption_id = str(caption_id).strip()
        print(f"{T.INFO}    {E.INFO} Attempting direct update with provided caption ID '{str_caption_id}'.")
        try:
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            # The body for an update needs the caption ID and the snippet
            response = youtube.captions().update(part="snippet", body={'id': str_caption_id, 'snippet': {'isDraft': False}}, media_body=media_body).execute()
            increment_quota('captions.update')
            print(f"{T.OK}    {E.SUCCESS} Update successful!")
            return response
        except HttpError as e:
            if e.resp.status == 404:
                print(f"{T.WARN}    {E.WARN} Provided caption ID '{str_caption_id}' not found. Will fall back to searching by language.")
            else:
                raise e

    print(f"{T.INFO}    {E.INFO} Searching for existing caption in '{normalized_lang}'...")
    caption_to_update = None
    try:
        list_response = list_captions(youtube, video_id)
        caption_to_update = next((item for item in list_response.get('items', []) if item['snippet']['language'].lower() == normalized_lang.lower()), None)
    except HttpError as e:
        print(f"{T.WARN}    {E.WARN} Could not check for existing captions: {e.reason}. Will try to upload as a new caption.")
        return upload_caption(youtube, video_id, normalized_lang, file_path)

    if caption_to_update:
        found_caption_id = caption_to_update['id']
        print(f"{T.INFO}    {E.INFO} Found existing caption with ID '{found_caption_id}'. Updating it.")
        try:
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            response = youtube.captions().update(part="snippet", body={'id': found_caption_id, 'snippet': {'isDraft': False}}, media_body=media_body).execute()
            increment_quota('captions.update')
            print(f"{T.OK}    {E.SUCCESS} Update successful!")
            return response
        except HttpError as e:
            print(f"{T.FAIL}{E.FAIL}  -> YouTube API error during update for caption ID {found_caption_id}: {e.reason}")
            print(f"{T.INFO}           Trying to upload as new caption instead.")
            return upload_caption(youtube, video_id, normalized_lang, file_path)
    else:
        print(f"{T.INFO}    {E.INFO} No existing '{normalized_lang}' caption found. Proceeding with a new upload.")
        return upload_caption(youtube, video_id, normalized_lang, file_path)

def delete_caption(youtube, caption_id, is_update=False):
    message_prefix = "  " if is_update else ""
    print(f"{T.INFO}{message_prefix}  {E.TRASH} Deleting caption with ID: {caption_id}...")
    youtube.captions().delete(id=caption_id).execute()
    increment_quota('captions.delete')
    print(f"{T.OK}{message_prefix}    {E.SUCCESS} Deleted caption.")