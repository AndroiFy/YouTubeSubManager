import os
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError

from src.config import (
    T, E, SCOPES, API_SERVICE_NAME, API_VERSION, CLIENT_SECRETS_FILE,
    normalize_language_code, validate_language_code
)

def get_authenticated_service(channel_nickname):
    """Handles OAuth 2.0 authentication and returns an authorized YouTube API service object."""
    token_file = f"token_{channel_nickname}.json"
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"{T.INFO}{E.INFO} Access token for '{channel_nickname}' expired. Refreshing automatically...")
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print(f"{T.WARN}{E.WARN} Token refresh failed: {e}. Please re-authenticate.")
                os.remove(token_file)
                creds = None

        if not creds:
            print(f"{T.WARN}{E.KEY} No valid token for '{channel_nickname}'. Please authenticate via the browser.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            print(f"{T.OK}{E.SUCCESS} Authentication successful. Token saved to '{token_file}'.")

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def get_channel_videos(youtube, channel_id):
    """Fetches all video IDs and titles for a given channel."""
    video_ids = []
    try:
        res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
        playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        next_page_token = None
        while True:
            res = youtube.playlistItems().list(
                playlistId=playlist_id, part='snippet', maxResults=50, pageToken=next_page_token
            ).execute()
            for item in res['items']:
                video_ids.append({'id': item['snippet']['resourceId']['videoId'], 'title': item['snippet']['title']})
            next_page_token = res.get('nextPageToken')
            if not next_page_token:
                break
    except HttpError as e:
        raise HttpError(f"Failed to get channel videos: {e.reason}", e.resp) from e

    print(f"{T.OK}Found {len(video_ids)} videos in the channel.")
    return video_ids

def upload_caption(youtube, video_id, language, file_path, dry_run=False):
    """Uploads a new caption track."""
    normalized_lang = normalize_language_code(language)
    if not validate_language_code(normalized_lang):
        print(f"{T.WARN}{E.WARN} Warning: '{normalized_lang}' may not be a valid YouTube language code.")

    print(f"{T.INFO}  {E.ROCKET} Preparing to upload '{normalized_lang}' caption from '{file_path}'...")
    if dry_run:
        print(f"{T.OK}    {E.SUCCESS} [DRY RUN] Would upload caption for language '{normalized_lang}'.")
        return

    body = {'snippet': {'videoId': video_id, 'language': normalized_lang, 'isDraft': False}}
    media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    try:
        response = youtube.captions().insert(part="snippet", body=body, media_body=media_body).execute()
        print(f"{T.OK}    {E.SUCCESS} Upload successful! Caption ID: {response['id']}.")
    except HttpError as e:
        raise HttpError(f"Failed to upload caption: {e.reason}", e.resp) from e

def update_caption(youtube, video_id, language, file_path, caption_id=None, dry_run=False):
    """Updates an existing caption track or uploads a new one if it doesn't exist."""
    normalized_lang = normalize_language_code(language)
    print(f"{T.INFO}  {E.PROCESS} Preparing to update '{normalized_lang}' caption for video {video_id}...")

    if dry_run:
        print(f"{T.OK}    {E.SUCCESS} [DRY RUN] Would update caption for language '{normalized_lang}'.")
        return

    is_valid_caption_id = pd.notna(caption_id) and str(caption_id).strip()

    if is_valid_caption_id:
        str_caption_id = str(caption_id).strip()
        print(f"{T.INFO}    {E.INFO} Attempting direct update with provided caption ID '{str_caption_id}'.")
        try:
            body = {'id': str_caption_id, 'snippet': {'videoId': video_id, 'isDraft': False}}
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            youtube.captions().update(part="snippet", body=body, media_body=media_body).execute()
            print(f"{T.OK}    {E.SUCCESS} Update successful!")
            return
        except HttpError as e:
            if e.resp.status == 404:
                print(f"{T.WARN}    {E.WARN} Provided caption ID '{str_caption_id}' not found. Falling back to search by language.")
            else:
                raise HttpError(f"Failed to update caption: {e.reason}", e.resp) from e

    print(f"{T.INFO}    {E.INFO} Searching for existing caption in '{normalized_lang}'...")
    try:
        list_response = youtube.captions().list(part="id,snippet", videoId=video_id).execute()
        caption_to_update = next((item for item in list_response.get('items', []) if item['snippet']['language'].lower() == normalized_lang.lower()), None)

        if caption_to_update:
            found_caption_id = caption_to_update['id']
            print(f"{T.INFO}    {E.INFO} Found existing caption with ID '{found_caption_id}'. Updating it.")
            body = {'id': found_caption_id, 'snippet': {'videoId': video_id, 'isDraft': False}}
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            youtube.captions().update(part="snippet", body=body, media_body=media_body).execute()
            print(f"{T.OK}    {E.SUCCESS} Update successful!")
        else:
            print(f"{T.INFO}    {E.INFO} No existing '{normalized_lang}' caption found. Uploading a new one.")
            upload_caption(youtube, video_id, normalized_lang, file_path, dry_run)

    except HttpError as e:
        print(f"{T.FAIL}{E.FAIL}  -> API error during update for language {normalized_lang}: {e.reason}")
        print(f"{T.INFO}           Trying to upload as new caption instead.")
        upload_caption(youtube, video_id, normalized_lang, file_path, dry_run)

def delete_caption(youtube, caption_id, dry_run=False):
    """Deletes a caption track."""
    print(f"{T.INFO}  {E.TRASH} Preparing to delete caption with ID: {caption_id}...")
    if dry_run:
        print(f"{T.OK}    {E.SUCCESS} [DRY RUN] Would delete caption with ID '{caption_id}'.")
        return

    try:
        youtube.captions().delete(id=caption_id).execute()
        print(f"{T.OK}    {E.SUCCESS} Deleted caption.")
    except HttpError as e:
        raise HttpError(f"Failed to delete caption: {e.reason}", e.resp) from e