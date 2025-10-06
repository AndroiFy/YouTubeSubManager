import sys
import os
import argparse
from src.config import T, E, load_config
from src.youtube_api import get_authenticated_service, upload_caption
from src.quota import display_quota_usage
from src.file_handler import (
    download_channel_captions_to_csv,
    generate_wide_report,
    process_csv_batch,
    create_project,
    sync_project,
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
    print(f"{E.FILE} project:   Creates a new project directory for managing subtitles.")
    print(f"{E.PROCESS} sync:      Synchronizes the project with YouTube, handling uploads, updates, and deletes.")
    print(f"{E.DOWNLOAD} download:  (For Processing) Creates a 'long' format CSV file with all subtitle data.")
    print(f"{E.REPORT} report:    (For Viewing) Creates a 'wide', human-readable CSV with one row per video.")
    print(f"{E.PROCESS} process:   Batch processes the 'long' CSV file created by the 'download' command.")
    print(f"{E.ROCKET} upload:    Uploads a single subtitle file to a video.")
    print(f"{E.ROCKET} smart-upload: Uploads one or more files by parsing their names.")

def main():
    """Main function to run the script."""
    if len(sys.argv) == 1:
        show_help()
        sys.exit(0)

    config = load_config()
    parser = argparse.ArgumentParser(description="Manage YouTube video subtitles for multiple channels.")
    parser.add_argument("-c", "--channel", required=True, choices=config['channels'].keys(), help="The nickname of the channel to work on (defined in config.json).")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Available commands")
    project_parser = subparsers.add_parser("project", help="Create a new project directory.")
    project_parser.add_argument("name", help="The name of the project.")

    sync_parser = subparsers.add_parser("sync", help="Synchronize a project with YouTube.")
    sync_parser.add_argument("name", help="The name of the project to sync.")

    subparsers.add_parser("download", help="Download all subtitle info to a 'long' CSV file for processing.")
    subparsers.add_parser("report", help="Generate a 'wide', human-readable CSV report for viewing.")

    process_parser = subparsers.add_parser("process", help="Process actions from a 'long' CSV file.")
    process_parser.add_argument("--csv-path", required=True, help="Path of the 'long' format CSV file to process.")

    upload_parser = subparsers.add_parser("upload", help="Upload a single subtitle file.")
    upload_parser.add_argument("--video-id", required=True)
    upload_parser.add_argument("--language", required=True)
    upload_parser.add_argument("--file-path", required=True)

    smart_upload_parser = subparsers.add_parser("smart-upload", help="Upload one or more files by parsing their names.")
    smart_upload_parser.add_argument("file_paths", nargs='+')

    args = parser.parse_args()

    try:
        channel_nickname = args.channel
        channel_id = config['channels'][channel_nickname]
        print(f"\n{T.HEADER}--- {E.CHANNEL} Working on channel: '{channel_nickname}' ---")
        youtube_service = get_authenticated_service(channel_nickname)

        if args.command == "project":
            create_project(youtube_service, channel_id, args.name)
        elif args.command == "sync":
            sync_project(youtube_service, args.name, channel_nickname)
        elif args.command == "download":
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
                if not os.access(file_path, os.R_OK):raise PermissionError(f"Cannot read file: {file_path}")
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
    finally:
        display_quota_usage()

if __name__ == "__main__":
    main()
