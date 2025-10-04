import os
import json
import re
from googleapiclient.errors import HttpError
from src.config import T, E
from src.translations import get_string
from src.youtube_api import upload_caption, update_caption, delete_caption
from src.utils import confirm_quota

def create_project(youtube, video_id):
    """Creates a project folder for a specific video, downloading existing subtitles and creating a status file."""
    print(get_string('project_creation_start', video_id=video_id))

    try:
        # 1. Get Video Details
        print(f"{T.INFO}  {get_string('project_fetch_video_details')}")
        video_response = youtube.videos().list(part="snippet", id=video_id).execute()
        if not video_response.get('items'):
            print(f"{T.FAIL}{E.FAIL} {get_string('project_failed_to_get_details', video_id=video_id)}")
            return
        video_title = video_response['items'][0]['snippet']['title']

        # Sanitize title for directory name
        sane_title = re.sub(r'[\\/*?:"<>|]',"", video_title)
        project_dir = os.path.join("projects", f"{video_id}_{sane_title}")
        subtitles_dir = os.path.join(project_dir, "subtitles")

        # 2. Create Directories
        print(f"{T.INFO}  {get_string('project_creating_directory', path=project_dir)}")
        os.makedirs(subtitles_dir, exist_ok=True)

        # 3. Fetch and Download Existing Captions
        print(f"{T.INFO}  {get_string('project_fetching_captions')}")
        captions_response = youtube.captions().list(part="snippet", videoId=video_id).execute()

        status_data = {
            "video_id": video_id,
            "title": video_title,
            "captions": []
        }

        for caption in captions_response.get('items', []):
            lang = caption['snippet']['language']
            caption_id = caption['id']
            print(f"{T.INFO}    {get_string('project_downloading_caption', lang=lang)}")
            try:
                # Download the caption file
                caption_body = youtube.captions().download(id=caption_id, tfmt="srt").execute()
                file_path = os.path.join(subtitles_dir, f"{lang}.srt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(caption_body)

                status_data["captions"].append({
                    "language": lang,
                    "caption_id": caption_id,
                    "file_path": os.path.relpath(file_path, project_dir)
                })
            except HttpError as e:
                print(f"{T.WARN}    {E.WARN} {get_string('project_failed_to_download_caption', caption_id=caption_id, lang=lang, reason=e.reason)}")

        # 4. Write status.json
        print(f"{T.INFO}  {get_string('project_writing_status')}")
        status_file_path = os.path.join(project_dir, "status.json")
        with open(status_file_path, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=4, ensure_ascii=False)

        print(f"\n{T.OK}{E.SUCCESS} {get_string('project_creation_complete', path=project_dir)}")

    except HttpError as e:
        print(f"\n{T.FAIL}{E.FAIL} {get_string('api_error_details', details=e.reason)}")
    except Exception as e:
        print(f"\n{T.FAIL}{E.FAIL} {get_string('unexpected_error', error=e)}")

def sync_project(youtube, project_path, allow_deletes=False, dry_run=False):
    """Syncs a project folder with YouTube, uploading, updating, and deleting subtitles as needed."""
    print(get_string('sync_start', project_path=project_path))

    status_file = os.path.join(project_path, 'status.json')
    subtitles_dir = os.path.join(project_path, 'subtitles')

    # 1. Read status.json
    print(f"{T.INFO}  {get_string('sync_reading_status')}")
    if not os.path.exists(status_file):
        print(f"{T.FAIL}{E.FAIL} status.json not found in project directory.")
        return
    with open(status_file, 'r', encoding='utf-8') as f:
        status_data = json.load(f)

    video_id = status_data['video_id']
    remote_captions = {caption['language']: caption for caption in status_data.get('captions', [])}

    # 2. Scan local files
    print(f"{T.INFO}  {get_string('sync_scanning_files')}")
    local_captions = {}
    for filename in os.listdir(subtitles_dir):
        if filename.endswith(".srt"):
            lang = os.path.splitext(filename)[0]
            local_captions[lang] = os.path.join(subtitles_dir, filename)

    # 3. Calculate actions
    print(f"{T.INFO}  {get_string('sync_calculating_actions')}")
    to_upload = {lang: path for lang, path in local_captions.items() if lang not in remote_captions}
    to_update = {lang: path for lang, path in local_captions.items() if lang in remote_captions}
    to_delete = {lang: data for lang, data in remote_captions.items() if lang not in local_captions}

    if not to_upload and not to_update and not to_delete:
        print(f"{T.OK}{E.SUCCESS} {get_string('sync_no_changes')}")
        return

    # 4. Display summary and get confirmation
    print(f"\n{T.HEADER}{get_string('sync_summary')}")
    if to_upload:
        print(f"{T.INFO}  {get_string('sync_upload_summary', count=len(to_upload), langs=', '.join(to_upload.keys()))}")
    if to_update:
        print(f"{T.INFO}  {get_string('sync_update_summary', count=len(to_update), langs=', '.join(to_update.keys()))}")
    if to_delete:
        print(f"{T.WARN}  {get_string('sync_delete_summary', count=len(to_delete), langs=', '.join(to_delete.keys()))}")
        if not allow_deletes:
            print(f"{T.WARN}    {get_string('sync_deletes_not_allowed')}")

    if not dry_run and not confirm_quota(uploads=len(to_upload), updates=len(to_update), deletes=len(to_delete) if allow_deletes else 0):
        return

    # 5. Perform actions
    print(f"\n{T.HEADER}{get_string('sync_performing_actions')}")
    for lang, path in to_upload.items():
        upload_caption(youtube, video_id, lang, path, dry_run)

    for lang, path in to_update.items():
        caption_id = remote_captions[lang]['caption_id']
        update_caption(youtube, video_id, lang, path, caption_id, dry_run)

    if allow_deletes:
        for lang, data in to_delete.items():
            delete_caption(youtube, data['caption_id'], dry_run)

    # 6. Update status file
    if not dry_run:
        print(f"\n{T.HEADER}{get_string('sync_updating_status_file')}")
        # Re-fetch captions to get the latest state
        new_captions_response = youtube.captions().list(part="snippet", videoId=video_id).execute()
        status_data['captions'] = []
        for caption in new_captions_response.get('items', []):
            lang = caption['snippet']['language']
            caption_id = caption['id']
            file_path = os.path.join("subtitles", f"{lang}.srt")
            status_data['captions'].append({
                "language": lang,
                "caption_id": caption_id,
                "file_path": file_path
            })
        with open(status_file, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=4, ensure_ascii=False)

    print(f"\n{T.OK}{E.SUCCESS} {get_string('sync_complete')}")