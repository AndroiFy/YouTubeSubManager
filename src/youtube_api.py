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

def get_authenticated_service(channel_nickname, translator):
    token_file = f"token_{channel_nickname}.json"
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print(translator.get('youtube_api.token_expired', channel_nickname=channel_nickname, T_INFO=T.INFO, E_INFO=E.INFO))
            try:
                creds.refresh(Request())
            except Exception as e:
                print(translator.get('youtube_api.token_refresh_failed', e=e, T_WARN=T.WARN, E_WARN=E.WARN))
                os.remove(token_file); creds = None
        if not creds:
            print(translator.get('youtube_api.no_valid_token', channel_nickname=channel_nickname, T_WARN=T.WARN, E_KEY=E.KEY))
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
            print(translator.get('youtube_api.auth_success', token_file=token_file, T_OK=T.OK, E_SUCCESS=E.SUCCESS))
    return build(API_SERVICE_NAME, API_VERSION, credentials=creds)

def get_channel_videos(youtube, channel_id, translator):
    """Retrieves all videos for a channel, using a cache to avoid redundant API calls."""
    cache_key = generate_cache_key("get_channel_videos", channel_id=channel_id)
    cached_videos = get_from_cache(cache_key, translator)
    if cached_videos:
        print(translator.get('youtube_api.cache_hit_videos', T_INFO=T.INFO, E_INFO=E.INFO))
        return cached_videos

    print(translator.get('youtube_api.fetching_videos', T_INFO=T.INFO, E_DOWNLOAD=E.DOWNLOAD))
    video_ids = []
    try:
        res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
        increment_quota('channels.list', translator)
        playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        next_page_token = None
        while True:
            res = youtube.playlistItems().list(playlistId=playlist_id, part='snippet', maxResults=50, pageToken=next_page_token).execute()
            increment_quota('playlistItems.list', translator)
            for item in res['items']:
                video_ids.append({'id': item['snippet']['resourceId']['videoId'], 'title': item['snippet']['title']})
            next_page_token = res.get('nextPageToken')
            if not next_page_token: break

        print(translator.get('youtube_api.found_videos', len_videos=len(video_ids), T_OK=T.OK))
        save_to_cache(cache_key, video_ids, translator)
        return video_ids
    except HttpError as e:
        print(translator.get('youtube_api.http_error', e=e, T_FAIL=T.FAIL, E_FAIL=E.FAIL))
        return []

def list_captions(youtube, video_id, translator):
    """
    Lists all captions for a video, using a cache to avoid redundant API calls.
    The caller is responsible for handling HttpError.
    """
    cache_key = generate_cache_key("list_captions", video_id=video_id)
    cached_captions = get_from_cache(cache_key, translator)
    if cached_captions is not None:
        return cached_captions

    response = youtube.captions().list(part="snippet", videoId=video_id).execute()
    increment_quota('captions.list', translator)
    save_to_cache(cache_key, response, translator)
    return response

def upload_caption(youtube, video_id, language, file_path, translator):
    """Uploads a caption and returns the API response."""
    normalized_lang = normalize_language_code(language, translator)
    if not validate_language_code(normalized_lang):
        print(translator.get('youtube_api.invalid_lang_code', normalized_lang=normalized_lang, T_WARN=T.WARN, E_WARN=E.WARN))

    print(translator.get('youtube_api.uploading_caption', normalized_lang=normalized_lang, file_path=file_path, T_INFO=T.INFO, E_ROCKET=E.ROCKET))
    body = {'snippet': {'videoId': video_id, 'language': normalized_lang, 'isDraft': False}}
    media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    response = youtube.captions().insert(part="snippet", body=body, media_body=media_body).execute()
    increment_quota('captions.insert', translator)
    print(translator.get('youtube_api.upload_success', caption_id=response['id'], T_OK=T.OK, E_SUCCESS=E.SUCCESS))
    return response

def update_caption(youtube, video_id, language, file_path, translator, caption_id=None):
    """Updates a caption and returns the API response."""
    normalized_lang = normalize_language_code(language, translator)
    print(translator.get('youtube_api.updating_caption', normalized_lang=normalized_lang, video_id=video_id, T_INFO=T.INFO, E_PROCESS=E.PROCESS))

    is_valid_caption_id = pd.notna(caption_id) and str(caption_id).strip()

    if is_valid_caption_id:
        str_caption_id = str(caption_id).strip()
        print(translator.get('youtube_api.update_direct', caption_id=str_caption_id, T_INFO=T.INFO, E_INFO=E.INFO))
        try:
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            response = youtube.captions().update(part="snippet", body={'id': str_caption_id, 'snippet': {'isDraft': False}}, media_body=media_body).execute()
            increment_quota('captions.update', translator)
            print(translator.get('youtube_api.update_success', T_OK=T.OK, E_SUCCESS=E.SUCCESS))
            return response
        except HttpError as e:
            if e.resp.status == 404:
                print(translator.get('youtube_api.caption_id_not_found', caption_id=str_caption_id, T_WARN=T.WARN, E_WARN=E.WARN))
            else:
                raise e

    print(translator.get('youtube_api.searching_by_lang', normalized_lang=normalized_lang, T_INFO=T.INFO, E_INFO=E.INFO))
    caption_to_update = None
    try:
        list_response = list_captions(youtube, video_id, translator)
        caption_to_update = next((item for item in list_response.get('items', []) if item['snippet']['language'].lower() == normalized_lang.lower()), None)
    except HttpError as e:
        print(translator.get('youtube_api.list_captions_failed', reason=e.reason, T_WARN=T.WARN, E_WARN=E.WARN))
        return upload_caption(youtube, video_id, normalized_lang, file_path, translator)

    if caption_to_update:
        found_caption_id = caption_to_update['id']
        print(translator.get('youtube_api.found_existing_caption', caption_id=found_caption_id, T_INFO=T.INFO, E_INFO=E.INFO))
        try:
            media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
            response = youtube.captions().update(part="snippet", body={'id': found_caption_id, 'snippet': {'isDraft': False}}, media_body=media_body).execute()
            increment_quota('captions.update', translator)
            print(translator.get('youtube_api.update_success', T_OK=T.OK, E_SUCCESS=E.SUCCESS))
            return response
        except HttpError as e:
            print(translator.get('youtube_api.update_api_error', caption_id=found_caption_id, reason=e.reason, T_FAIL=T.FAIL, E_FAIL=E.FAIL))
            print(translator.get('youtube_api.trying_new_upload', T_INFO=T.INFO))
            return upload_caption(youtube, video_id, normalized_lang, file_path, translator)
    else:
        print(translator.get('youtube_api.no_existing_caption', normalized_lang=normalized_lang, T_INFO=T.INFO, E_INFO=E.INFO))
        return upload_caption(youtube, video_id, normalized_lang, file_path, translator)

def delete_caption(youtube, caption_id, translator, is_update=False):
    message_prefix = "  " if is_update else ""
    print(translator.get('youtube_api.deleting_caption', caption_id=caption_id, T_INFO=T.INFO, E_TRASH=E.TRASH, message_prefix=message_prefix))
    youtube.captions().delete(id=caption_id).execute()
    increment_quota('captions.delete', translator)
    print(translator.get('youtube_api.delete_success', T_OK=T.OK, E_SUCCESS=E.SUCCESS, message_prefix=message_prefix))