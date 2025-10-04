import pandas as pd
from googleapiclient.errors import HttpError
from src.config import T, E, QUOTA_COSTS
from src.youtube_api import (
    get_channel_videos,
    upload_caption,
    update_caption,
    delete_caption
)
from src.translations import get_string
from src.utils import confirm_quota

def download_channel_captions_to_csv(youtube, channel_id, channel_nickname, no_cache=False):
    """Creates a CSV file with subtitle information for batch processing."""
    csv_path = f"captions_{channel_nickname}.csv"
    print(f"{T.INFO}{E.DOWNLOAD} {get_string('fetching_channel_info')}")

    videos = get_channel_videos(youtube, channel_id, no_cache=no_cache)
    all_captions_data = []

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} {get_string('processing_video', current=i+1, total=len(videos), title=video_title[:50])}")
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
            print(f"{T.WARN}    {E.WARN} {get_string('http_error_for_video', status=e.resp.status, reason=e.reason)}")
            all_captions_data.append({
                'video_id': video_id, 'video_title': video_title, 'caption_id': 'ERROR_FETCHING',
                'language': '', 'action': '', 'file_path': ''
            })

    df = pd.DataFrame(all_captions_data, columns=['video_id', 'video_title', 'caption_id', 'language', 'action', 'file_path'])
    df.to_csv(csv_path, index=False, encoding='utf-8')
    print(f"\n{T.OK}{E.SUCCESS} {get_string('csv_creation_successful', path=csv_path)}")

def generate_wide_report(youtube, channel_id, channel_nickname, no_cache=False):
    """Creates a human-readable CSV report of subtitle availability."""
    report_path = f"report_{channel_nickname}.csv"
    print(f"{T.INFO}{E.REPORT} {get_string('generating_report')}")

    videos = get_channel_videos(youtube, channel_id, no_cache=no_cache)
    all_videos_data, all_languages = [], set()

    for i, video in enumerate(videos):
        video_id, video_title = video['id'], video['title']
        print(f"{T.INFO}  {E.PROCESS} {get_string('processing_video', current=i+1, total=len(videos), title=video_title[:50])}")
        video_row = {'video_id': video_id, 'video_title': video_title}
        try:
            response = youtube.captions().list(part="snippet", videoId=video_id).execute()
            if response.get('items'):
                for caption in response['items']:
                    lang = caption['snippet']['language']
                    all_languages.add(lang)
                    video_row[f'caption_id_{lang}'] = caption['id']
        except HttpError as e:
            print(f"{T.WARN}    {E.WARN} {get_string('http_error_for_video', status=e.resp.status, reason=e.reason)}")
        all_videos_data.append(video_row)

    if not all_videos_data:
        print(f"{T.WARN}{E.WARN} {get_string('no_videos_for_report')}"); return

    columns = ['video_id', 'video_title'] + sorted([f'caption_id_{lang}' for lang in all_languages])
    df = pd.DataFrame(all_videos_data, columns=columns)
    df.to_csv(report_path, index=False, encoding='utf-8')
    print(f"\n{T.OK}{E.SUCCESS} {get_string('report_creation_successful', path=report_path)}")

def _estimate_quota_cost(df):
    """Estimates the total API quota cost for the actions in the DataFrame."""
    action_counts = df['action'].str.upper().value_counts()
    total_cost = 0
    for action, count in action_counts.items():
        total_cost += QUOTA_COSTS.get(action, 0) * count
    return total_cost, action_counts

def process_csv_batch(youtube, csv_path, dry_run=False):
    """Processes subtitle operations from a CSV file."""
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print(f"{T.FAIL}{E.FAIL} {get_string('csv_not_found', path=csv_path)}")
        return

    actions_df = df[df['action'].notna()].copy()
    actions_df['action'] = actions_df['action'].str.strip().str.upper()

    if actions_df.empty:
        print(f"{T.WARN}{E.WARN} {get_string('no_actions_in_csv')}"); return

    total_cost, action_counts = _estimate_quota_cost(actions_df)
    if not dry_run and not confirm_quota(
        uploads=action_counts.get('UPLOAD', 0),
        updates=action_counts.get('UPDATE', 0),
        deletes=action_counts.get('DELETE', 0)
    ):
        return

    for index, row in actions_df.iterrows():
        action = row.get('action', '')
        video_id = row.get('video_id', '')
        lang = row.get('language', '')
        file_path = row.get('file_path', '')
        caption_id = row.get('caption_id', '')

        print(f"\n{T.HEADER}{get_string('processing_row', row_num=index+2, action=action, video_id=video_id)}")

        try:
            if action == 'UPLOAD':
                upload_caption(youtube, video_id, str(lang), str(file_path), dry_run=dry_run)
            elif action == 'UPDATE':
                update_caption(youtube, video_id, str(lang), str(file_path), caption_id=caption_id, dry_run=dry_run)
            elif action == 'DELETE':
                delete_caption(youtube, str(caption_id), dry_run=dry_run)
            else:
                print(f"{T.WARN}{E.WARN}  {get_string('skipping_action', action=action)}")
        except FileNotFoundError as e:
            print(f"{T.FAIL}{E.FAIL}  {get_string('file_not_found_error', error=e)}")
        except PermissionError as e:
            print(f"{T.FAIL}{E.FAIL}  {get_string('permission_error', error=e)}")
        except HttpError as e:
            try:
                error_details = e.reason
                if e.content:
                    error_json = pd.io.json.loads(e.content.decode('utf-8'))
                    error_message = error_json.get("error", {}).get("message", e.reason)
                    error_details = f"{error_message} (Code: {e.resp.status})"
                print(f"{T.FAIL}{E.FAIL}  {get_string('youtube_api_error', error=error_details)}")
            except (ValueError, AttributeError):
                print(f"{T.FAIL}{E.FAIL}  {get_string('youtube_api_error', error=f'{e.reason} (Code: {e.resp.status})')}")
        except Exception as e:
            print(f"{T.FAIL}{E.FAIL}  {get_string('unexpected_row_error', error=e)}")