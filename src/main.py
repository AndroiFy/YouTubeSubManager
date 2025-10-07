import sys
import os
import argparse
from src.config import T, E, load_config
from src.youtube_api import get_authenticated_service, upload_caption
from src.quota import display_quota_usage
from src.localization import Translator
from src.file_handler import (
    download_channel_captions_to_csv,
    generate_wide_report,
    process_csv_batch,
    create_project,
    sync_project,
)

def show_help(translator):
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
    print(translator.get('main.welcome'))
    print(translator.get('main.commands_header'))
    print(f"{E.FILE} project:   {translator.get('help.project')}")
    print(f"{E.PROCESS} sync:      {translator.get('help.sync')}")
    print(f"{E.DOWNLOAD} download:  {translator.get('help.download')}")
    print(f"{E.REPORT} report:    {translator.get('help.report')}")
    print(f"{E.PROCESS} process:   {translator.get('help.process')}")
    print(f"{E.ROCKET} upload:    {translator.get('help.upload')}")
    print(f"{E.ROCKET} smart-upload: {translator.get('help.smart_upload')}")

def main():
    """Main function to run the script."""
    # Quick parse for language argument before full parsing
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("-l", "--language", default='en', help="Set the display language (e.g., 'en', 'es').")
    pre_args, _ = pre_parser.parse_known_args()

    translator = Translator(pre_args.language)

    if len(sys.argv) == 1 or (len(sys.argv) == 3 and ('-l' in sys.argv or '--language' in sys.argv)):
        show_help(translator)
        sys.exit(0)

    config = load_config()
    parser = argparse.ArgumentParser(description=translator.get('args.description'))
    parser.add_argument("-c", "--channel", required=True, choices=config['channels'].keys(), help=translator.get('args.channel'))
    parser.add_argument("-l", "--language", default='en', help="Set the display language (e.g., 'en', 'es').")

    subparsers = parser.add_subparsers(dest="command", required=True, help=translator.get('args.command'))
    project_parser = subparsers.add_parser("project", help=translator.get('args.project_help'))
    project_parser.add_argument("name", help=translator.get('args.project_name'))

    sync_parser = subparsers.add_parser("sync", help=translator.get('args.sync_help'))
    sync_parser.add_argument("name", help=translator.get('args.sync_name'))

    subparsers.add_parser("download", help=translator.get('args.download_help'))
    subparsers.add_parser("report", help=translator.get('args.report_help'))

    process_parser = subparsers.add_parser("process", help=translator.get('args.process_help'))
    process_parser.add_argument("--csv-path", required=True, help=translator.get('args.csv_path'))

    upload_parser = subparsers.add_parser("upload", help=translator.get('args.upload_help'))
    upload_parser.add_argument("--video-id", required=True)
    upload_parser.add_argument("--language", required=True)
    upload_parser.add_argument("--file-path", required=True)

    smart_upload_parser = subparsers.add_parser("smart-upload", help=translator.get('args.smart_upload_help'))
    smart_upload_parser.add_argument("file_paths", nargs='+')

    args = parser.parse_args()

    try:
        channel_nickname = args.channel
        channel_id = config['channels'][channel_nickname]
        print(translator.get('main.working_on_channel', E_CHANNEL=E.CHANNEL, channel_nickname=channel_nickname))
        youtube_service = get_authenticated_service(channel_nickname, translator)

        if args.command == "project":
            create_project(youtube_service, channel_id, args.name, translator)
        elif args.command == "sync":
            sync_project(youtube_service, args.name, channel_nickname, translator)
        elif args.command == "download":
            download_channel_captions_to_csv(youtube_service, channel_id, channel_nickname, translator)
        elif args.command == "report":
            generate_wide_report(youtube_service, channel_id, channel_nickname, translator)
        elif args.command == "process":
            process_csv_batch(youtube_service, args.csv_path, translator)
        elif args.command == "upload":
            upload_caption(youtube_service, args.video_id, args.language, args.file_path, translator)
        elif args.command == "smart-upload":
            print(translator.get('smart_upload.header', E_ROCKET=E.ROCKET))
            print(translator.get('smart_upload.validating'))
            target_video_id, files_to_upload = None, []
            for file_path in args.file_paths:
                if not os.path.exists(file_path): raise FileNotFoundError(translator.get('smart_upload.file_not_found', file_path=file_path))
                if not os.access(file_path, os.R_OK):raise PermissionError(translator.get('smart_upload.permission_denied', file_path=file_path))
                basename = os.path.basename(file_path)
                filename_no_ext, _ = os.path.splitext(basename)
                parts = filename_no_ext.rsplit('_', 1)
                if len(parts) != 2 or not parts[0] or not parts[1]: raise ValueError(translator.get('smart_upload.invalid_format', basename=basename))
                video_id, language = parts
                if target_video_id is None:
                    target_video_id = video_id
                    print(translator.get('smart_upload.video_id_set', E_VIDEO=E.VIDEO, target_video_id=target_video_id))
                elif video_id != target_video_id:
                    raise ValueError(translator.get('smart_upload.mismatched_id', target_video_id=target_video_id, basename=basename, video_id=video_id))
                files_to_upload.append({'path': file_path, 'id': video_id, 'lang': language})
            print(translator.get('smart_upload.validation_success', E_SUCCESS=E.SUCCESS))
            print(translator.get('smart_upload.starting_uploads', len_files_to_upload=len(files_to_upload)))
            for i, file_info in enumerate(files_to_upload):
                print(f"{T.INFO}   ({i+1}/{len(files_to_upload)}) ", end="")
                upload_caption(youtube_service, file_info['id'], file_info['lang'], file_info['path'], translator)
            print(translator.get('smart_upload.complete', E_SUCCESS=E.SUCCESS))

    except Exception as e:
        print(translator.get('main.fatal_error', e=e))
        sys.exit(1)
    finally:
        display_quota_usage(translator)

if __name__ == "__main__":
    main()