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

def download_channel_captions_to_csv(youtube, channel_id, channel_nickname, translator):
    """Creates a CSV file with subtitle information for batch processing."""
    csv_path = f"captions_{channel_nickname}.csv"
    print(translator.get('file_handler.download_start', T_INFO=T.INFO, E_DOWNLOAD=E.DOWNLOAD))

    videos = get_channel_videos(youtube, channel_id, translator)
    all_captions_data = []

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(translator.get('file_handler.processing_video', T_INFO=T.INFO, E_PROCESS=E.PROCESS, i=i+1, len_videos=len(videos), video_title=video_title[:50]))
        try:
            response = list_captions(youtube, video_id, translator)
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
            print(translator.get('file_handler.http_error_video', T_WARN=T.WARN, E_WARN=E.WARN, code=e.code, reason=e.reason))
            all_captions_data.append({
                'video_id': video_id, 'video_title': video_title, 'caption_id': 'ERROR_FETCHING',
                'language': '', 'action': '', 'file_path': ''
            })

    df = pd.DataFrame(all_captions_data, columns=['video_id', 'video_title', 'caption_id', 'language', 'action', 'file_path'])
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(translator.get('file_handler.download_success', T_OK=T.OK, E_SUCCESS=E.SUCCESS, csv_path=csv_path))

def generate_wide_report(youtube, channel_id, channel_nickname, translator):
    """Creates a human-readable CSV report of subtitle availability."""
    report_path = f"report_{channel_nickname}.csv"
    print(translator.get('file_handler.report_start', T_INFO=T.INFO, E_REPORT=E.REPORT))

    videos = get_channel_videos(youtube, channel_id, translator)
    all_videos_data, all_languages = [], set()

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(translator.get('file_handler.processing_video', T_INFO=T.INFO, E_PROCESS=E.PROCESS, i=i+1, len_videos=len(videos), video_title=video_title[:50]))
        video_row = {'video_id': video_id, 'video_title': video_title}
        try:
            response = list_captions(youtube, video_id, translator)
            if response.get('items'):
                for caption in response['items']:
                    lang = caption['snippet']['language']
                    all_languages.add(lang)
                    video_row[f'caption_id_{lang}'] = caption['id']
        except HttpError as e:
            print(translator.get('file_handler.http_error_video', T_WARN=T.WARN, E_WARN=E.WARN, code=e.code, reason=e.reason))
        all_videos_data.append(video_row)

    if not all_videos_data:
        print(translator.get('file_handler.report_no_videos', T_WARN=T.WARN, E_WARN=E.WARN)); return

    columns = ['video_id', 'video_title'] + sorted([f'caption_id_{lang}' for lang in all_languages])
    df = pd.DataFrame(all_videos_data, columns=columns)
    df.to_csv(report_path, index=False, encoding='utf-8')
    print(translator.get('file_handler.report_success', T_OK=T.OK, E_SUCCESS=E.SUCCESS, report_path=report_path))

def process_csv_batch(youtube, csv_path, translator):
    """Processes subtitle operations from a CSV file."""
    if not os.path.exists(csv_path): raise FileNotFoundError(f"CSV file not found at '{csv_path}'")
    print(translator.get('file_handler.process_start', T_INFO=T.INFO, E_PROCESS=E.PROCESS, csv_path=csv_path))
    df = pd.read_csv(csv_path)
    actions_df = df[df['action'].notna()].copy()
    actions_df['action'] = actions_df['action'].str.strip().str.upper()

    if actions_df.empty:
        print(translator.get('file_handler.process_no_actions', T_WARN=T.WARN, E_WARN=E.WARN)); return

    for index, row in actions_df.iterrows():
        action = row.get('action', '')
        video_id = row.get('video_id', '')
        lang = row.get('language', '')
        file_path = row.get('file_path', '')
        caption_id = row.get('caption_id', '')

        print(translator.get('file_handler.process_row_header', T_HEADER=T.HEADER, index=index+2, action=action, video_id=video_id))

        try:
            if action == 'UPLOAD':
                upload_caption(youtube, video_id, str(lang), str(file_path), translator)
            elif action == 'UPDATE':
                update_caption(youtube, video_id, str(lang), str(file_path), translator, caption_id=caption_id)
            elif action == 'DELETE':
                delete_caption(youtube, str(caption_id), translator)
            else:
                print(translator.get('file_handler.skipping_action', T_WARN=T.WARN, E_WARN=E.WARN, action=action))
        except FileNotFoundError as e:
            print(translator.get('file_handler.file_not_found', T_FAIL=T.FAIL, E_FAIL=E.FAIL, e=e))
        except PermissionError as e:
            print(translator.get('file_handler.permission_denied', T_FAIL=T.FAIL, E_FAIL=E.FAIL, e=e))
        except HttpError as e:
            print(translator.get('file_handler.youtube_api_error', T_FAIL=T.FAIL, E_FAIL=E.FAIL, code=e.code, reason=e.reason))
        except Exception as e:
            print(translator.get('file_handler.unexpected_error', T_FAIL=T.FAIL, E_FAIL=E.FAIL, e=e))

def create_project(youtube, channel_id, project_name, translator):
    """Creates a new project directory and populates it with subtitle data."""
    project_path = os.path.join("projects", project_name)
    if os.path.exists(project_path):
        print(translator.get('project.already_exists', T_FAIL=T.FAIL, E_FAIL=E.FAIL, project_name=project_name, project_path=project_path))
        return

    os.makedirs(project_path, exist_ok=True)
    print(translator.get('project.created_directory', T_OK=T.OK, E_SUCCESS=E.SUCCESS, project_path=project_path))

    print(translator.get('project.fetching_data', T_INFO=T.INFO, E_DOWNLOAD=E.DOWNLOAD))
    videos = get_channel_videos(youtube, channel_id, translator)
    project_data = {}

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(translator.get('file_handler.processing_video', T_INFO=T.INFO, E_PROCESS=E.PROCESS, i=i+1, len_videos=len(videos), video_title=video_title[:50]))

        video_data = { "title": video_title, "subtitles": {} }

        try:
            response = list_captions(youtube, video_id, translator)
            for caption in response.get('items', []):
                lang = caption['snippet']['language']
                video_data["subtitles"][lang] = {
                    "caption_id": caption['id'], "last_updated": caption['snippet'].get('lastUpdated'),
                    "is_draft": caption['snippet'].get('isDraft'), "local_path": "",
                    "last_sync": None, "status": "synced"
                }
        except HttpError as e:
            print(translator.get('project.http_error_video', T_WARN=T.WARN, E_WARN=E.WARN, code=e.code, video_id=video_id, reason=e.reason))
            video_data["error"] = f"HTTP {e.code}: {e.reason}"

        project_data[video_id] = video_data

    subtitles_json_path = os.path.join(project_path, "subtitles.json")
    with open(subtitles_json_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=4, ensure_ascii=False)

    print(translator.get('project.create_success', T_OK=T.OK, E_SUCCESS=E.SUCCESS, project_name=project_name))
    print(translator.get('project.data_saved', T_INFO=T.INFO, E_FILE=E.FILE, subtitles_json_path=subtitles_json_path))

def sync_project(youtube, project_name, channel_nickname, translator):
    """Synchronizes the project with YouTube, handling uploads, updates, and deletions."""
    project_path = os.path.join("projects", project_name)
    subtitles_json_path = os.path.join(project_path, "subtitles.json")

    if not os.path.exists(subtitles_json_path):
        print(translator.get('project.not_found', T_FAIL=T.FAIL, E_FAIL=E.FAIL, project_name=project_name))
        return

    with open(subtitles_json_path, 'r', encoding='utf-8') as f:
        project_data = json.load(f)

    print(translator.get('sync.header', T_HEADER=T.HEADER, E_PROCESS=E.PROCESS, project_name=project_name))
    print(translator.get('sync.scanning', T_INFO=T.INFO))

    local_files = {}
    for root, _, files in os.walk(project_path):
        for file in files:
            if not file.endswith(".srt"):
                continue

            # Path of the current subtitle file
            full_path = os.path.join(root, file)

            # Strategy 1: New structure (projects/my_project/VIDEO_ID/LANG.srt)
            parent_dir = os.path.basename(root)
            if parent_dir in project_data:
                video_id = parent_dir
                lang = os.path.splitext(file)[0]

                # New structure takes precedence.
                local_files[(video_id, lang)] = full_path
                continue

            # Strategy 2: Old structure (projects/my_project/VIDEO_ID_LANG.srt)
            if root == project_path:
                try:
                    video_id, lang = os.path.splitext(file)[0].split('_', 1)
                    if video_id in project_data:
                        # Add only if not already found via the new structure.
                        if (video_id, lang) not in local_files:
                            local_files[(video_id, lang)] = full_path
                    else:
                        print(translator.get('sync.invalid_format', T_WARN=T.WARN, file=file))
                except ValueError:
                    print(translator.get('sync.invalid_format', T_WARN=T.WARN, file=file))

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
            sub_info = { "caption_id": None, "local_path": local_path, "status": "new", "last_sync": None }
            project_data[video_id]['subtitles'][lang] = sub_info
            actions_to_perform.append(('upload', video_id, lang, sub_info))

    print(translator.get('sync.analyzing', T_INFO=T.INFO))
    for action, video_id, lang, sub_info in actions_to_perform:
        try:
            if action == 'upload':
                print(translator.get('sync.uploading', T_INFO=T.INFO, E_ROCKET=E.ROCKET, video_id=video_id, lang=lang))
                response = upload_caption(youtube, video_id, lang, sub_info['local_path'], translator)
                sub_info.update({
                    'caption_id': response['id'], 'status': 'synced',
                    'last_sync': datetime.now(timezone.utc).isoformat(),
                    'last_updated': response['snippet']['lastUpdated']
                })
            elif action == 'update':
                print(translator.get('sync.updating', T_INFO=T.INFO, E_PROCESS=E.PROCESS, video_id=video_id, lang=lang))
                response = update_caption(youtube, video_id, lang, sub_info['local_path'], translator, caption_id=sub_info['caption_id'])
                sub_info.update({
                    'status': 'synced', 'last_sync': datetime.now(timezone.utc).isoformat(),
                    'last_updated': response['snippet']['lastUpdated']
                })
            elif action == 'delete':
                print(translator.get('sync.deleting', T_INFO=T.INFO, E_TRASH=E.TRASH, video_id=video_id, lang=lang))
                delete_caption(youtube, sub_info['caption_id'], translator)
                del project_data[video_id]['subtitles'][lang]
        except Exception as e:
            print(translator.get('sync.failed_action', T_FAIL=T.FAIL, E_FAIL=E.FAIL, action=action, video_id=video_id, lang=lang, e=e))
            sub_info['status'] = f'error: {e}'

    print(translator.get('sync.saving', T_INFO=T.INFO))
    with open(subtitles_json_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=4, ensure_ascii=False)

    print(translator.get('sync.complete', T_OK=T.OK, E_SUCCESS=E.SUCCESS, project_name=project_name))