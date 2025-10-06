import os
import json
import pandas as pd
from googleapiclient.errors import HttpError
from src.config import T, E
from datetime import datetime, timezone
from src.youtube_api import (
    get_channel_videos,
    upload_caption,
    update_caption,
    delete_caption,
    list_captions
)

def download_channel_captions_to_csv(youtube, channel_id, channel_nickname):
    """Creates a CSV file with subtitle information for batch processing."""
    csv_path = f"captions_{channel_nickname}.csv"
    print(f"{T.INFO}{E.DOWNLOAD} Starting to fetch channel information for processing file...")

    videos = get_channel_videos(youtube, channel_id)
    all_captions_data = []

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} Processing video {i+1}/{len(videos)}: {video_title[:50]}...")
        try:
            response = list_captions(youtube, video_id)
            if not response.get('items'):
                all_captions_data.append({'video_id': video_id, 'video_title': video_title, 'caption_id': '', 'language': '', 'action': '', 'file_path': ''})
            else:
                for idx, caption in enumerate(response['items']):
                    title_to_use = video_title if idx == 0 else ''
                    all_captions_data.append({
                        'video_id': video_id, 'video_title': title_to_use, 'caption_id': caption['id'],
                        'language': caption['snippet']['language'], 'action': '', 'file_path': ''
                    })
        except HttpError as e:
            print(f"{T.WARN}    {E.WARN} An HTTP error {e.code} occurred for this video: {e.reason}")
            all_captions_data.append({
                'video_id': video_id, 'video_title': video_title, 'caption_id': 'ERROR_FETCHING',
                'language': '', 'action': '', 'file_path': ''
            })

    df = pd.DataFrame(all_captions_data, columns=['video_id', 'video_title', 'caption_id', 'language', 'action', 'file_path'])
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n{T.OK}{E.SUCCESS} Successfully created processing file at: {csv_path}")

def generate_wide_report(youtube, channel_id, channel_nickname):
    """Creates a human-readable CSV report of subtitle availability."""
    report_path = f"report_{channel_nickname}.csv"
    print(f"{T.INFO}{E.REPORT} Starting to generate wide format report. This may take a while...")

    videos = get_channel_videos(youtube, channel_id)
    all_videos_data, all_languages = [], set()

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} Processing video {i+1}/{len(videos)}: {video_title[:50]}...")
        video_row = {'video_id': video_id, 'video_title': video_title}
        try:
            response = list_captions(youtube, video_id)
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
    """Processes subtitle operations from a CSV file."""
    if not os.path.exists(csv_path): raise FileNotFoundError(f"CSV file not found at '{csv_path}'")
    print(f"{T.INFO}{E.PROCESS} Processing CSV file: {csv_path}")
    df = pd.read_csv(csv_path)
    actions_df = df[df['action'].notna()].copy()
    actions_df['action'] = actions_df['action'].str.strip().str.upper()

    if actions_df.empty:
        print(f"{T.WARN}{E.WARN} No actions found in the CSV file."); return

    for index, row in actions_df.iterrows():
        action = row.get('action', '')
        video_id = row.get('video_id', '')
        lang = row.get('language', '')
        file_path = row.get('file_path', '')
        caption_id = row.get('caption_id', '')

        print(f"\n{T.HEADER}--- Processing Row {index+2}: Action='{action}', VideoID='{video_id}' ---")

        try:
            if action == 'UPLOAD':
                upload_caption(youtube, video_id, str(lang), str(file_path))
            elif action == 'UPDATE':
                update_caption(youtube, video_id, str(lang), str(file_path), caption_id=caption_id)
            elif action == 'DELETE':
                delete_caption(youtube, str(caption_id))
            else:
                print(f"{T.WARN}{E.WARN}  -> SKIPPING: Unknown action '{action}'")
        except FileNotFoundError as e:
            print(f"{T.FAIL}{E.FAIL}  -> File not found: {e}")
        except PermissionError as e:
            print(f"{T.FAIL}{E.FAIL}  -> Permission denied: {e}")
        except HttpError as e:
            print(f"{T.FAIL}{E.FAIL}  -> YouTube API error {e.code}: {e.reason}")
        except Exception as e:
            print(f"{T.FAIL}{E.FAIL}  -> Unexpected error: {e}")

def create_project(youtube, channel_id, project_name):
    """Creates a new project directory and populates it with subtitle data."""
    project_path = os.path.join("projects", project_name)
    if os.path.exists(project_path):
        print(f"{T.FAIL}{E.FAIL} Project '{project_name}' already exists at: {project_path}")
        return

    os.makedirs(project_path, exist_ok=True)
    print(f"{T.OK}{E.SUCCESS} Created project directory: {project_path}")

    print(f"{T.INFO}{E.DOWNLOAD} Fetching all video and subtitle data for the channel...")
    videos = get_channel_videos(youtube, channel_id)
    project_data = {}

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} Processing video {i+1}/{len(videos)}: {video_title[:50]}...")

        video_data = {
            "title": video_title,
            "subtitles": {}
        }

        try:
            response = list_captions(youtube, video_id)
            for caption in response.get('items', []):
                lang = caption['snippet']['language']
                video_data["subtitles"][lang] = {
                    "caption_id": caption['id'],
                    "last_updated": caption['snippet'].get('lastUpdated'),
                    "is_draft": caption['snippet'].get('isDraft'),
                    "local_path": "",
                    "last_sync": None,
                    "status": "synced"
                }
        except HttpError as e:
            print(f"{T.WARN}    {E.WARN} An HTTP error {e.code} occurred for video {video_id}: {e.reason}")
            video_data["error"] = f"HTTP {e.code}: {e.reason}"

        project_data[video_id] = video_data

    subtitles_json_path = os.path.join(project_path, "subtitles.json")
    with open(subtitles_json_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=4, ensure_ascii=False)

    print(f"\n{T.OK}{E.SUCCESS} Project '{project_name}' created successfully.")
    print(f"{T.INFO}{E.FILE} Subtitle data saved to: {subtitles_json_path}")

def sync_project(youtube, project_name, channel_nickname):
    """Synchronizes the project with YouTube, handling uploads, updates, and deletions."""
    project_path = os.path.join("projects", project_name)
    subtitles_json_path = os.path.join(project_path, "subtitles.json")

    if not os.path.exists(subtitles_json_path):
        print(f"{T.FAIL}{E.FAIL} Project '{project_name}' not found. Please create it first.")
        return

    with open(subtitles_json_path, 'r', encoding='utf-8') as f:
        project_data = json.load(f)

    print(f"{T.HEADER}--- {E.PROCESS} Starting Sync for Project: {project_name} ---")

    # 1. Scan local files and determine their status
    print(f"{T.INFO}1. Scanning for local subtitle files and changes...")

    local_files = {}
    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(".srt"):
                try:
                    video_id, lang = os.path.splitext(file)[0].split('_', 1)
                    local_files[(video_id, lang)] = os.path.join(root, file)
                except ValueError:
                    print(f"{T.WARN}   Skipping file with invalid format: {file}")

    actions_to_perform = []
    for video_id, video_info in project_data.items():
        for lang, sub_info in video_info.get("subtitles", {}).items():
            file_key = (video_id, lang)
            if file_key in local_files:
                local_path = local_files.pop(file_key)
                sub_info['local_path'] = local_path

                last_sync_time = datetime.fromisoformat(sub_info['last_sync']) if sub_info.get('last_sync') else datetime.min.replace(tzinfo=timezone.utc)
                local_mod_time = datetime.fromtimestamp(os.path.getmtime(local_path)).astimezone(timezone.utc)

                if local_mod_time > last_sync_time:
                    sub_info['status'] = 'modified'
                    actions_to_perform.append(('update', video_id, lang, sub_info))
                else:
                    sub_info['status'] = 'synced'
            else:
                sub_info['status'] = 'deleted'
                actions_to_perform.append(('delete', video_id, lang, sub_info))

    for (video_id, lang), local_path in local_files.items():
        if video_id in project_data:
            sub_info = {
                "caption_id": None, "local_path": local_path,
                "status": "new", "last_sync": None
            }
            project_data[video_id]['subtitles'][lang] = sub_info
            actions_to_perform.append(('upload', video_id, lang, sub_info))

    # 2. Execute sync operations
    print(f"\n{T.INFO}2. Executing synchronization actions...")
    for action, video_id, lang, sub_info in actions_to_perform:
        try:
            if action == 'upload':
                print(f"{T.INFO}  {E.ROCKET} Uploading new subtitle for video {video_id} ({lang})...")
                response = upload_caption(youtube, video_id, lang, sub_info['local_path'])
                sub_info.update({
                    'caption_id': response['id'], 'status': 'synced',
                    'last_sync': datetime.now(timezone.utc).isoformat(),
                    'last_updated': response['snippet']['lastUpdated']
                })
            elif action == 'update':
                print(f"{T.INFO}  {E.PROCESS} Updating subtitle for video {video_id} ({lang})...")
                response = update_caption(youtube, video_id, lang, sub_info['local_path'], sub_info['caption_id'])
                sub_info.update({
                    'status': 'synced', 'last_sync': datetime.now(timezone.utc).isoformat(),
                    'last_updated': response['snippet']['lastUpdated']
                })
            elif action == 'delete':
                print(f"{T.INFO}  {E.TRASH} Deleting subtitle for video {video_id} ({lang})...")
                delete_caption(youtube, sub_info['caption_id'])
                # Remove from project data
                del project_data[video_id]['subtitles'][lang]
        except Exception as e:
            print(f"{T.FAIL}{E.FAIL}  -> FAILED to {action} for video {video_id} ({lang}): {e}")
            sub_info['status'] = f'error: {e}'

    # 3. Save updated project data
    print(f"\n{T.INFO}3. Saving updated project file...")
    with open(subtitles_json_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=4, ensure_ascii=False)

    print(f"\n{T.OK}--- {E.SUCCESS} Sync Complete for Project: {project_name} ---")