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

def show_help():
    """Displays the main help message."""
    print(rf"""
{T.HEADER}╔══════════════════════════════════════════════════╗
║                                                  ║
║        Y O U T U B E   S U B T I T L E S         ║
║                    M A N A G E R                 ║
║                      v6.0                        ║
║                                                  ║
╚══════════════════════════════════════════════════╝
""")
    print(" Welcome! This tool helps manage subtitles for multiple YouTube channels.")
    print("\n--- Available Commands ---\n")
    print(f"{E.DOWNLOAD} download:  Creates a CSV file with all subtitle data.")
    print(f"{E.REPORT} report:    Creates a human-readable report of subtitle status.")
    print(f"{E.PROCESS} process:   Batch processes actions from a CSV file.")
    print(f"{E.ROCKET} upload:    Uploads a single subtitle file.")
    print(f"{E.ROCKET} smart-upload: Uploads one or more files by parsing their names.")

def main():
    """Main function to run the script."""
    if len(sys.argv) == 1:
        show_help()
        sys.exit(0)

    config = load_config()
    parser = argparse.ArgumentParser(description="Manage YouTube video subtitles.")
    parser.add_argument("-c", "--channel", required=True, choices=config['channels'].keys(), help="Channel nickname from config.json.")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("--dry-run", action="store_true", help="Simulate actions without making any changes to YouTube.")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    subparsers.add_parser("download", help="Download subtitle info to a CSV.")
    subparsers.add_parser("report", help="Generate a wide CSV report.")

    process_parser = subparsers.add_parser("process", help="Process a CSV file.", parents=[parent_parser])
    process_parser.add_argument("--csv-path", required=True, help="Path to the CSV file.")

    upload_parser = subparsers.add_parser("upload", help="Upload a single file.", parents=[parent_parser])
    upload_parser.add_argument("--video-id", required=True)
    upload_parser.add_argument("--language", required=True)
    upload_parser.add_argument("--file-path", required=True)

    smart_upload_parser = subparsers.add_parser("smart-upload", help="Upload files based on their names.", parents=[parent_parser])
    smart_upload_parser.add_argument("file_paths", nargs='+')

    args = parser.parse_args()

    is_dry_run = getattr(args, 'dry_run', False)
    if is_dry_run:
        print(f"{T.WARN}--- DRY RUN mode enabled: No changes will be made ---")

    try:
        channel_nickname = args.channel
        channel_id = config['channels'][channel_nickname]
        print(f"\n{T.HEADER}--- {E.CHANNEL} Working on channel: '{channel_nickname}' ---")

        modifying_commands = ["process", "upload", "smart-upload"]
        youtube = None
        if not (args.command in modifying_commands and is_dry_run):
            youtube = get_authenticated_service(channel_nickname)

        if args.command == "download":
            download_channel_captions_to_csv(youtube, channel_id, channel_nickname)
        elif args.command == "report":
            generate_wide_report(youtube, channel_id, channel_nickname)
        elif args.command == "process":
            process_csv_batch(youtube, args.csv_path, dry_run=is_dry_run)
        elif args.command == "upload":
            upload_caption(youtube, args.video_id, args.language, args.file_path, dry_run=is_dry_run)
        elif args.command == "smart-upload":
            print(f"{T.HEADER}--- {E.ROCKET} Starting Smart Upload ---")
            print(f"{T.INFO}1. Validating all file names...")
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
                    raise ValueError(f"Invalid filename format for '{basename}'. Expected 'VIDEOID_LANGUAGE.ext'.")

                language = components[-1]
                video_id = '_'.join(components[:-1])

                if not video_id or not language:
                    raise ValueError(f"Invalid filename format for '{basename}'. Video ID or language part is empty.")

                if target_video_id is None:
                    target_video_id = video_id
                    print(f"{T.INFO}   {E.VIDEO} Target Video ID set to: {target_video_id}")
                elif video_id != target_video_id:
                    raise ValueError(f"Mismatched Video ID. Expected '{target_video_id}' but file '{basename}' has '{video_id}'.")
                files_to_upload.append({'path': file_path, 'id': video_id, 'lang': language})

            print(f"{T.OK}   {E.SUCCESS} Validation successful.")
            print(f"\n{T.INFO}2. Starting uploads for {len(files_to_upload)} files...")
            for i, file_info in enumerate(files_to_upload):
                print(f"{T.INFO}   ({i+1}/{len(files_to_upload)}) ", end="")
                upload_caption(youtube, file_info['id'], file_info['lang'], file_info['path'], dry_run=is_dry_run)
            print(f"\n{T.OK}--- {E.SUCCESS} Smart Upload Complete ---")

    except (ValueError, FileNotFoundError, PermissionError) as e:
        print(f"\n{T.FAIL}{E.FAIL} Input Error: {e}")
        sys.exit(1)
    except HttpError as e:
        try:
            error_details = e.reason
            if e.content:
                error_json = pd.io.json.loads(e.content.decode('utf-8'))
                error_message = error_json.get("error", {}).get("message", e.reason)
                error_details = f"{error_message} (Code: {e.resp.status})"
            print(f"\n{T.FAIL}{E.FAIL} YouTube API Error: {error_details}")
        except (ValueError, AttributeError):
            print(f"\n{T.FAIL}{E.FAIL} YouTube API Error: {e.reason} (Code: {e.resp.status})")
        sys.exit(1)
    except Exception as e:
        print(f"\n{T.FAIL}{E.FAIL} An unexpected fatal error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
