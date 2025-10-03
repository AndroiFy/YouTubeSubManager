import pandas as pd
from googleapiclient.errors import HttpError
from src.config import T, E
from src.youtube_api import (
    get_channel_videos,
    upload_caption,
    update_caption,
    delete_caption
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
            response = youtube.captions().list(part="snippet", videoId=video_id).execute()
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
            print(f"{T.WARN}    {E.WARN} An HTTP error {e.resp.status} occurred for this video: {e.reason}")
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
    print(f"{T.INFO}{E.REPORT} Starting to generate wide format report...")

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
            print(f"{T.WARN}    {E.WARN} An HTTP error {e.resp.status} occurred for this video: {e.reason}")
        all_videos_data.append(video_row)

    if not all_videos_data:
        print(f"{T.WARN}{E.WARN} No videos found to generate a report."); return

    columns = ['video_id', 'video_title'] + sorted([f'caption_id_{lang}' for lang in all_languages])
    df = pd.DataFrame(all_videos_data, columns=columns)
    df.to_csv(report_path, index=False, encoding='utf-8')
    print(f"\n{T.OK}{E.SUCCESS} Successfully created wide format report at: {report_path}")

def process_csv_batch(youtube, csv_path, dry_run=False):
    """Processes subtitle operations from a CSV file."""
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"{T.FAIL}{E.FAIL} CSV file not found at '{csv_path}'")
        return

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
                upload_caption(youtube, video_id, str(lang), str(file_path), dry_run=dry_run)
            elif action == 'UPDATE':
                update_caption(youtube, video_id, str(lang), str(file_path), caption_id=caption_id, dry_run=dry_run)
            elif action == 'DELETE':
                delete_caption(youtube, str(caption_id), dry_run=dry_run)
            else:
                print(f"{T.WARN}{E.WARN}  -> SKIPPING: Unknown action '{action}'")
        except FileNotFoundError as e:
            print(f"{T.FAIL}{E.FAIL}  -> File not found: {e}")
        except PermissionError as e:
            print(f"{T.FAIL}{E.FAIL}  -> Permission denied: {e}")
        except HttpError as e:
            try:
                error_details = e.reason
                if e.content:
                    error_json = pd.io.json.loads(e.content.decode('utf-8'))
                    error_message = error_json.get("error", {}).get("message", e.reason)
                    error_details = f"{error_message} (Code: {e.resp.status})"
                print(f"{T.FAIL}{E.FAIL}  -> YouTube API error: {error_details}")
            except (ValueError, AttributeError):
                print(f"{T.FAIL}{E.FAIL}  -> YouTube API error: {e.reason} (Code: {e.resp.status})")
        except Exception as e:
            print(f"{T.FAIL}{E.FAIL}  -> An unexpected error occurred: {e}")