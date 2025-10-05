import sys
import os
import argparse
import pandas as pd
from googleapiclient.errors import HttpError
from src.config import T, E, load_config
from src.youtube_api import get_authenticated_service, upload_caption
from src.file_handler import (
    download_channel_captions_to_csv,
    generate_wide_report,
    process_csv_batch,
)
from src.translations import get_string, load_translations
from src.utils import confirm_quota

def show_help():
    """Displays the main help message."""
    print(rf"""
{T.HEADER}╔══════════════════════════════════════════════════╗
║                                                        ║
║        Y O U T U B E   S U B T I T L E S               ║
║                    M A N A G E R                       ║
║                      v6.0                              ║
║                                                        ║
╚══════════════════════════════════════════════════════╝
""")
    print(get_string('welcome_message'))
    print("\n--- Available Commands ---\n")
    print(f"{E.DOWNLOAD} download:  {get_string('help_download')}")
    print(f"{E.REPORT} report:    {get_string('help_report')}")
    print(f"{E.PROCESS} process:   {get_string('help_process')}")
    print(f"{E.ROCKET} upload:    {get_string('help_upload')}")
    print(f"{E.ROCKET} smart-upload: {get_string('help_smart_upload')}")
    print(f"{E.ROCKET} smart-upload: {get_string('help_smart_upload')}")

def main():
    """Main function to run the script."""
    # Preliminary parse to get the language, so help messages can be translated.
    lang_parser = argparse.ArgumentParser(add_help=False)
    lang_parser.add_argument('--lang', default='en', help="Application language (e.g., en, it, fr).")
    lang_args, _ = lang_parser.parse_known_args()
    load_translations(lang_args.lang)

    if len(sys.argv) == 1:
        show_help()
        sys.exit(0)

    config = load_config()
    parser = argparse.ArgumentParser(description=get_string('app_description'))
    parser.add_argument("-c", "--channel", required=True, choices=config['channels'].keys(), help=get_string('channel_help'))
    parser.add_argument('--lang', default='en', help=get_string('lang_help'))

    # Parent parsers for flags
    dry_run_parser = argparse.ArgumentParser(add_help=False)
    dry_run_parser.add_argument("--dry-run", action="store_true", help=get_string('dry_run_help'))

    cache_parser = argparse.ArgumentParser(add_help=False)
    cache_parser.add_argument("--no-cache", action="store_true", help=get_string('no_cache_help'))


    subparsers = parser.add_subparsers(dest="command", required=True, help=get_string('commands_help'))

    download_parser = subparsers.add_parser("download", help=get_string('download_help'), parents=[cache_parser])
    report_parser = subparsers.add_parser("report", help=get_string('report_help'), parents=[cache_parser])

    process_parser = subparsers.add_parser("process", help=get_string('process_help'), parents=[dry_run_parser])
    process_parser.add_argument("--csv-path", required=True, help=get_string('csv_path_help'))

    upload_parser = subparsers.add_parser("upload", help=get_string('upload_help'), parents=[dry_run_parser])
    upload_parser.add_argument("--video-id", required=True)
    upload_parser.add_argument("--language", required=True)
    upload_parser.add_argument("--file-path", required=True)

    smart_upload_parser = subparsers.add_parser("smart-upload", help=get_string('smart_upload_help'), parents=[dry_run_parser])
    smart_upload_parser.add_argument("file_paths", nargs='+')

    args = parser.parse_args()

    is_dry_run = getattr(args, 'dry_run', False)
    if is_dry_run:
        print(f"{T.WARN}{get_string('dry_run_enabled')}")

    is_no_cache = getattr(args, 'no_cache', False)

    try:
        channel_nickname = args.channel
        channel_id = config['channels'][channel_nickname]
        print(f"\n{T.HEADER}{get_string('working_on_channel', channel_nickname=channel_nickname)}")

        modifying_commands = ["process", "upload", "smart-upload"]
        youtube = None
        if not (args.command in modifying_commands and is_dry_run):
            youtube = get_authenticated_service(channel_nickname)

        if args.command == "download":
            download_channel_captions_to_csv(youtube, channel_id, channel_nickname, no_cache=is_no_cache)
        elif args.command == "report":
            generate_wide_report(youtube, channel_id, channel_nickname, no_cache=is_no_cache)
        elif args.command == "process":
            process_csv_batch(youtube, args.csv_path, dry_run=is_dry_run)
        elif args.command == "upload":
            if not is_dry_run and not confirm_quota(uploads=1, updates=0, deletes=0):
                sys.exit(0)
            upload_caption(youtube, args.video_id, args.language, args.file_path, dry_run=is_dry_run)
        elif args.command == "smart-upload":
            if not is_dry_run and not confirm_quota(uploads=len(args.file_paths), updates=0, deletes=0):
                sys.exit(0)

            print(f"{T.HEADER}--- {E.ROCKET} {get_string('smart_upload_start')} ---")
            print(f"{T.INFO}{get_string('validating_files')}")
            target_video_id, files_to_upload = None, []
            for file_path in args.file_paths:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"The file '{file_path}' was not found.")
                if not os.access(file_path, os.R_OK):
                    raise PermissionError(f"Cannot read file: {file_path}")

                basename = os.path.basename(file_path)
                filename_no_ext, _ = os.path.splitext(basename)

                components = filename_no_ext.split('_')
                if len(components) < 2:
                    raise ValueError(get_string('invalid_filename', basename=basename))

                language = components[-1]
                video_id = '_'.join(components[:-1])

                if not video_id or not language:
                    raise ValueError(get_string('empty_filename_parts', basename=basename))

                if target_video_id is None:
                    target_video_id = video_id
                    print(f"{T.INFO}   {E.VIDEO} {get_string('target_video_id_set', target_video_id=target_video_id)}")
                elif video_id != target_video_id:
                    raise ValueError(get_string('mismatched_video_id', target_video_id=target_video_id, basename=basename, video_id=video_id))
                files_to_upload.append({'path': file_path, 'id': video_id, 'lang': language})

            print(f"{T.OK}   {E.SUCCESS} {get_string('validation_successful')}")
            print(f"\n{T.INFO}{get_string('starting_uploads', file_count=len(files_to_upload))}")
            for i, file_info in enumerate(files_to_upload):
                print(f"{T.INFO}   ({i+1}/{len(files_to_upload)}) ", end="")
                upload_caption(youtube, file_info['id'], file_info['lang'], file_info['path'], dry_run=is_dry_run)
            print(f"\n{T.OK}--- {E.SUCCESS} {get_string('smart_upload_complete')} ---")

    except (ValueError, FileNotFoundError, PermissionError) as e:
        print(f"\n{T.FAIL}{E.FAIL} {get_string('input_error', error=e)}")
        sys.exit(1)
    except HttpError as e:
        try:
            error_details = e.reason
            if e.content:
                error_json = pd.io.json.loads(e.content.decode('utf-8'))
                error_message = error_json.get("error", {}).get("message", e.reason)
                error_details = f"{error_message} (Code: {e.resp.status})"
            print(f"\n{T.FAIL}{E.FAIL} {get_string('api_error_details', details=error_details)}")
        except (ValueError, AttributeError):
            print(f"\n{T.FAIL}{E.FAIL} {get_string('api_error_details', details=f'{e.reason} (Code: {e.resp.status})')}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{T.FAIL}{E.FAIL} {get_string('unexpected_error', error=e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()