import os
import sys
import json
import argparse
import pandas as pd

from colorama import init, Fore, Style
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

init(autoreset=True)

# --- Style Definitions ---
class T:
    HEADER, OK, INFO, WARN, FAIL = Fore.MAGENTA + Style.BRIGHT, Fore.GREEN + Style.BRIGHT, Fore.CYAN, Fore.YELLOW, Fore.RED + Style.BRIGHT

# CORRECTED E CLASS
class E:
    SUCCESS, INFO, WARN, FAIL, KEY, ROCKET, CHANNEL, FILE, DOWNLOAD, PROCESS, VIDEO, TRASH, REPORT = "✅", "ℹ️", "⚠️", "❌", "🔑", "🚀", "📺", "📁", "📥", "⚙️", "🎞️", "🗑️", "📊"

# --- Configuration ---
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME, API_VERSION, CLIENT_SECRETS_FILE, CONFIG_FILE = "youtube", "v3", "client_secrets.json", "config.json"

# --- Core Functions ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"{T.FAIL}{E.FAIL} Configuration file '{CONFIG_FILE}' not found. Please create it.")
        sys.exit(1)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

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
    video_ids = []
    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    next_page_token = None
    while True:
        res = youtube.playlistItems().list(playlistId=playlist_id, part='snippet', maxResults=50, pageToken=next_page_token).execute()
        for item in res['items']:
            video_ids.append({'id': item['snippet']['resourceId']['videoId'], 'title': item['snippet']['title']})
        next_page_token = res.get('nextPageToken')
        if not next_page_token: break
    print(f"{T.OK}Found {len(video_ids)} videos in the channel.")
    return video_ids

def download_channel_captions_to_csv(youtube, channel_id, channel_nickname):
    csv_path = f"captions_{channel_nickname}.csv"
    print(f"{T.INFO}{E.DOWNLOAD} Starting to fetch channel information for processing file...")
    videos = get_channel_videos(youtube, channel_id)
    all_captions_data = []
    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} Processing video {i+1}/{len(videos)}: {video_title[:50]}...")
        try:
            response = youtube.captions().list(part="snippet", videoId=video_id).execute()
            if not response.get('items'):
                all_captions_data.append({'video_id': video_id, 'video_title': video_title, 'caption_id': '', 'language': '', 'action': '', 'file_path': ''})
            else:
                for idx, caption in enumerate(response['items']):
                    title_to_use = video_title if idx == 0 else ''
                    all_captions_data.append({'video_id': video_id, 'video_title': title_to_use, 'caption_id': caption['id'], 'language': caption['snippet']['language'], 'action': '', 'file_path': ''})
        except HttpError as e:
            print(f"{T.WARN}    {E.WARN} An HTTP error {e.code} occurred for this video: {e.reason}")
            all_captions_data.append({'video_id': video_id, 'video_title': video_title, 'caption_id': 'ERROR_FETCHING', 'language': '', 'action': '', 'file_path': ''})
    df = pd.DataFrame(all_captions_data, columns=['video_id', 'video_title', 'caption_id', 'language', 'action', 'file_path'])
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n{T.OK}{E.SUCCESS} Successfully created processing file at: {csv_path}")

def generate_wide_report(youtube, channel_id, channel_nickname):
    report_path = f"report_{channel_nickname}.csv"
    print(f"{T.INFO}{E.REPORT} Starting to generate wide format report. This may take a while...")
    videos = get_channel_videos(youtube, channel_id)
    all_videos_data, all_languages = [], set()
    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} Processing video {i+1}/{len(videos)}: {video_title[:50]}...")
        video_row = {'video_id': video_id, 'video_title': video_title}
        try:
            response = youtube.captions().list(part="snippet", videoId=video_id).execute()
            if response.get('items'):
                for caption in response['items']:
                    lang = caption['snippet']['language']
                    all_languages.add(lang)
                    video_row[f'caption_id_{lang}'] = caption['id']
        except HttpError as e:
            print(f"{T.WARN}    {E.WARN} An HTTP error {e.code} occurred for this video: {e.reason}")
        all_videos_data.append(video_row)
    if not all_videos_data:
        print(f"{T.WARN}{E.WARN} No videos found to generate a report."); return
    columns = ['video_id', 'video_title'] + sorted([f'caption_id_{lang}' for lang in all_languages])
    df = pd.DataFrame(all_videos_data, columns=columns)
    df.to_csv(report_path, index=False, encoding='utf-8')
    print(f"\n{T.OK}{E.SUCCESS} Successfully created wide format report at: {report_path}")

def process_csv_batch(youtube, csv_path):
    if not os.path.exists(csv_path): raise FileNotFoundError(f"CSV file not found at '{csv_path}'")
    print(f"{T.INFO}{E.PROCESS} Processing CSV file: {csv_path}")
    df = pd.read_csv(csv_path)
    actions_df = df[df['action'].notna()].copy()
    actions_df['action'] = actions_df['action'].str.strip().str.upper()
    if actions_df.empty:
        print(f"{T.WARN}{E.WARN} No actions found in the CSV file."); return
    for index, row in actions_df.iterrows():
        action, video_id, caption_id, lang, file_path = row['action'], row['video_id'], row['caption_id'], row['language'], row['file_path']
        print(f"\n{T.HEADER}--- Processing Row {index+2}: Action='{action}', VideoID='{video_id}' ---")
        try:
            if action == 'UPLOAD': upload_caption(youtube, video_id, str(lang), str(file_path))
            elif action == 'UPDATE': update_caption(youtube, video_id, str(lang), str(file_path))
            elif action == 'DELETE': delete_caption(youtube, str(caption_id))
            else: print(f"{T.WARN}{E.WARN}  -> SKIPPING: Unknown action '{action}'")
        except Exception as e: print(f"{T.FAIL}{E.FAIL}  -> An error occurred: {e}")

def upload_caption(youtube, video_id, language, file_path):
    print(f"{T.INFO}  {E.ROCKET} Uploading '{language}' caption from '{file_path}'...")
    body = {'snippet': {'videoId': video_id, 'language': language, 'isDraft': False}}
    media_body = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    response = youtube.captions().insert(part="snippet", body=body, media_body=media_body).execute()
    print(f"{T.OK}    {E.SUCCESS} Upload successful! Caption ID: {response['id']}.")

def update_caption(youtube, video_id, language, file_path):
    print(f"{T.INFO}  {E.PROCESS} Updating '{language}' caption for video {video_id}...")
    try:
        response = youtube.captions().list(part="snippet", videoId=video_id).execute()
        caption_id_to_delete = next((item['id'] for item in response.get('items', []) if item['snippet']['language'].lower() == language.lower()), None)
        if caption_id_to_delete:
            delete_caption(youtube, caption_id_to_delete, is_update=True)
        else:
            print(f"{T.INFO}    {E.INFO} No existing '{language}' caption found. Proceeding with a new upload.")
    except HttpError as e:
        print(f"{T.WARN}    {E.WARN} Could not check for existing captions: {e.reason}. Attempting to upload anyway.")
    upload_caption(youtube, video_id, language, file_path)

def delete_caption(youtube, caption_id, is_update=False):
    message_prefix = "  " if is_update else ""
    print(f"{T.INFO}{message_prefix}  {E.TRASH} Deleting caption with ID: {caption_id}...")
    youtube.captions().delete(id=caption_id).execute()
    print(f"{T.OK}{message_prefix}    {E.SUCCESS} Deleted caption.")

# --- Main Execution Block ---
if __name__ == "__main__":
    if len(sys.argv) == 1:
        print(rf"""
{T.HEADER}╔════════════════════════════════════════════════════════╗
║                                                        ║
║        Y O U T U B E   S U B T I T L E S                 ║
║                    M A N A G E R                         ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
""")
        print(" Welcome! This tool helps manage subtitles for multiple YouTube channels.")
        print(f" It is configured to use the channels defined in '{T.OK}{CONFIG_FILE}'.")
        print("\n--- Available Commands ---\n")
        print(f"{E.DOWNLOAD} download:  (For Processing) Creates a 'long' format CSV file with all subtitle data.")
        print("   Usage:     python codev2.py --channel <nickname> download\n")
        print(f"{E.REPORT} report:    (For Viewing) Creates a 'wide', human-readable CSV with one row per video.")
        print("   Usage:     python codev2.py --channel <nickname> report\n")
        print(f"{E.PROCESS} process:   Batch processes the 'long' CSV file created by the 'download' command.")
        print("   Usage:     python codev2.py --channel <nickname> process --csv-path <path_to_long_csv>\n")
        print(f"{E.ROCKET} upload:    Uploads a single subtitle file to a video.")
        print("   Usage:     python codev2.py --channel <nickname> upload --video-id ID --language en --file-path file.srt\n")
        print(f"{E.ROCKET} smart-upload: Uploads one or more files by parsing their names.")
        print("   Usage:     python codev2.py --channel <nickname> smart-upload FILE1_lang.srt ...\n")

        # === NEW: Custom Credit Information ===
        # Replace the placeholder text below with your actual information.
        print(f"{T.HEADER}----------------------------------------------------------")
        print(f"{T.INFO}   Script created and updated by: [Your Name/Alias]")
        print(f"{T.INFO}   YouTube: [Your YouTube Channel URL]")
        print(f"{T.INFO}   GitHub:  [Your GitHub Repository URL]")
        print(f"{T.HEADER}----------------------------------------------------------")
        
        sys.exit(0)

    config = load_config()
    parser = argparse.ArgumentParser(description="Manage YouTube video subtitles for multiple channels.")
    parser.add_argument("-c", "--channel", required=True, choices=config['channels'].keys(), help="The nickname of the channel to work on (defined in config.json).")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")

    parser_download = subparsers.add_parser("download", help="Download all subtitle info to a 'long' CSV file for processing.")
    parser_report = subparsers.add_parser("report", help="Generate a 'wide', human-readable CSV report for viewing.")
    parser_process = subparsers.add_parser("process", help="Process actions from a 'long' CSV file.")
    parser_process.add_argument("--csv-path", required=True, help="Path of the 'long' format CSV file to process.")
    parser_upload = subparsers.add_parser("upload", help="Upload a single subtitle file.")
    parser_upload.add_argument("--video-id", required=True)
    parser_upload.add_argument("--language", required=True)
    parser_upload.add_argument("--file-path", required=True)
    parser_smart_upload = subparsers.add_parser("smart-upload", help="Upload one or more files by parsing their names.")
    parser_smart_upload.add_argument("file_paths", nargs='+')
    
    args = parser.parse_args()
    
    try:
        channel_nickname = args.channel
        channel_id = config['channels'][channel_nickname]
        print(f"\n{T.HEADER}--- {E.CHANNEL} Working on channel: '{channel_nickname}' ---")
        youtube_service = get_authenticated_service(channel_nickname)
        
        if args.command == "download":
            download_channel_captions_to_csv(youtube_service, channel_id, channel_nickname)
        elif args.command == "report":
            generate_wide_report(youtube_service, channel_id, channel_nickname)
        elif args.command == "process":
            process_csv_batch(youtube_service, args.csv_path)
        elif args.command == "upload":
            upload_caption(youtube_service, args.video_id, args.language, args.file_path)
        elif args.command == "smart-upload":
            print(f"{T.HEADER}--- {E.ROCKET} Starting Smart Upload ---")
            print(f"{T.INFO}1. Validating all file names...")
            target_video_id, files_to_upload = None, []
            for file_path in args.file_paths:
                if not os.path.exists(file_path): raise FileNotFoundError(f"The file '{file_path}' was not found.")
                basename = os.path.basename(file_path)
                filename_no_ext, _ = os.path.splitext(basename)
                parts = filename_no_ext.rsplit('_', 1)
                if len(parts) != 2 or not parts[0] or not parts[1]: raise ValueError(f"Invalid filename format for '{basename}'. Must be 'VIDEOID_LANGUAGE.ext'.")
                video_id, language = parts
                if target_video_id is None:
                    target_video_id = video_id
                    print(f"{T.INFO}   {E.VIDEO} Target Video ID set to: {target_video_id}")
                elif video_id != target_video_id:
                    raise ValueError(f"Mismatched Video ID. Expected '{target_video_id}' but file '{basename}' has '{video_id}'.")
                files_to_upload.append({'path': file_path, 'id': video_id, 'lang': language})
            print(f"{T.OK}   {E.SUCCESS} Validation successful. All files are for the same video.")
            print(f"\n{T.INFO}2. Starting uploads for {len(files_to_upload)} files...")
            for i, file_info in enumerate(files_to_upload):
                print(f"{T.INFO}   ({i+1}/{len(files_to_upload)}) ", end="")
                upload_caption(youtube_service, file_info['id'], file_info['lang'], file_info['path'])
            print(f"\n{T.OK}--- {E.SUCCESS} Smart Upload Complete ---")
    except Exception as e:
        print(f"\n{T.FAIL}{E.FAIL} FATAL ERROR: An operation failed. Reason: {e}")
        sys.exit(1)