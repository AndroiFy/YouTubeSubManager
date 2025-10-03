import os
import json
import json
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
from src.translations import get_string

def get_authenticated_service(channel_nickname):
    """Handles OAuth 2.0 authentication and returns an authorized YouTube API service object."""
    token_file = f"token_{channel_nickname}.json"
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(f"{T.INFO}{E.INFO} {get_string('token_expired', channel_nickname=channel_nickname)}")
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print(f"{T.WARN}{E.WARN} {get_string('token_refresh_failed', error=e)}")
                os.remove(token_file)
                creds = None

        if not creds:
            print(f"{T.WARN}{E.KEY} {get_string('no_valid_token', channel_nickname=channel_nickname)}")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            print(f"{T.OK}{E.SUCCESS} {get_string('auth_successful', token_file=token_file)}")

    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def get_channel_videos(youtube, channel_id, no_cache=False):
    """Fetches all video IDs and titles for a given channel, with caching."""
    cache_dir = "cache"
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = f"{cache_dir}/{channel_id}_videos.json"

    if not no_cache and os.path.exists(cache_file):
        print(f"{T.INFO}    {E.INFO} Loading video list from cache...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            video_ids = json.load(f)
        print(f"{T.OK}{get_string('videos_found', count=len(video_ids))}")
        return video_ids

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
        raise HttpError(get_string('get_videos_failed', reason=e.reason), e.resp) from e

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(video_ids, f, ensure_ascii=False, indent=4)

    print(f"{T.OK}{get_string('videos_found', count=len(video_ids))}")
    return video_ids

def upload_caption(youtube, video_id, language, file_path, dry_run=False):
    """Uploads a new caption track."""
    normalized_lang = normalize_language_code(language)
    if not validate_language_code(normalized_lang):
        print(f"{T.WARN}{E.WARN} {get_string('lang_code_warning', lang=normalized_lang)}")

    print(f"{T.INFO}  {E.ROCKET} {get_string('upload_prep', lang=normalized_lang, path=file_path)}")
    if dry_run:
        print(f"{T.OK}    {E.SUCCESS} {get_string('dry_run_upload', lang=normalized_lang)}")
        return

    body = {'snippet': {'videoId': video_id, 'language': normalized_lang, 'isDraft': False}}
    media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)

    try:
        response = youtube.captions().insert(part="snippet", body=body, media_body=media_body).execute()
        print(f"{T.OK}    {E.SUCCESS} {get_string('upload_successful', caption_id=response['id'])}")
    except HttpError as e:
        raise HttpError(get_string('upload_failed', reason=e.reason), e.resp) from e

def update_caption(youtube, video_id, language, file_path, caption_id=None, dry_run=False):
    """Updates an existing caption track or uploads a new one if it doesn't exist."""
    normalized_lang = normalize_language_code(language)
    print(f"{T.INFO}  {E.PROCESS} {get_string('update_prep', lang=normalized_lang, video_id=video_id)}")

    if dry_run:
        print(f"{T.OK}    {E.SUCCESS} {get_string('dry_run_update', lang=normalized_lang)}")
        return

    is_valid_caption_id = pd.notna(caption_id) and str(caption_id).strip()

    if is_valid_caption_id:
        str_caption_id = str(caption_id).strip()
        print(f"{T.INFO}    {E.INFO} {get_string('update_direct_attempt', caption_id=str_caption_id)}")
        try:
            body = {'id': str_caption_id, 'snippet': {'videoId': video_id, 'isDraft': False}}
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            youtube.captions().update(part="snippet", body=body, media_body=media_body).execute()
            print(f"{T.OK}    {E.SUCCESS} {get_string('update_successful')}")
            return
        except HttpError as e:
            if e.resp.status == 404:
                print(f"{T.WARN}    {E.WARN} {get_string('update_id_not_found', caption_id=str_caption_id)}")
            else:
                raise HttpError(get_string('update_failed', reason=e.reason), e.resp) from e

    print(f"{T.INFO}    {E.INFO} {get_string('searching_for_caption', lang=normalized_lang)}")
    try:
        list_response = youtube.captions().list(part="id,snippet", videoId=video_id).execute()
        caption_to_update = next((item for item in list_response.get('items', []) if item['snippet']['language'].lower() == normalized_lang.lower()), None)

        if caption_to_update:
            found_caption_id = caption_to_update['id']
            print(f"{T.INFO}    {E.INFO} {get_string('found_existing_caption', caption_id=found_caption_id)}")
            body = {'id': found_caption_id, 'snippet': {'videoId': video_id, 'isDraft': False}}
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            youtube.captions().update(part="snippet", body=body, media_body=media_body).execute()
            print(f"{T.OK}    {E.SUCCESS} {get_string('update_successful')}")
        else:
            print(f"{T.INFO}    {E.INFO} {get_string('no_existing_caption', lang=normalized_lang)}")
            upload_caption(youtube, video_id, normalized_lang, file_path, dry_run)

    except HttpError as e:
        print(f"{T.FAIL}{E.FAIL}  -> {get_string('update_api_error', lang=normalized_lang, reason=e.reason)}")
        print(f"{T.INFO}           {get_string('uploading_instead')}")
        upload_caption(youtube, video_id, normalized_lang, file_path, dry_run)

def delete_caption(youtube, caption_id, dry_run=False):
    """Deletes a caption track."""
    print(f"{T.INFO}  {E.TRASH} {get_string('delete_prep', caption_id=caption_id)}")
    if dry_run:
        print(f"{T.OK}    {E.SUCCESS} {get_string('dry_run_delete', caption_id=caption_id)}")
        return

    try:
        youtube.captions().delete(id=caption_id).execute()
        print(f"{T.OK}    {E.SUCCESS} {get_string('delete_successful')}")
    except HttpError as e:
        raise HttpError(get_string('delete_failed', reason=e.reason), e.resp) from e