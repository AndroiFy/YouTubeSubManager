# YouTube Subtitles Manager

> 🎬 A powerful Python tool for managing YouTube video subtitles across multiple channels

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![YouTube API](https://img.shields.io/badge/YouTube%20API-v3-red.svg)](https://developers.google.com/youtube/v3)

## 🚀 Features

- 📺 **Multi-Channel Support** - Manage subtitles for multiple YouTube channels
- 📊 **Batch Processing** - Upload/update/delete multiple subtitle files at once
- 🎨 **Beautiful Interface** - Colorful terminal output with emojis
- 📈 **Detailed Reports** - Generate comprehensive subtitle reports
- 🔄 **Smart Upload** - Auto-detect video IDs and languages from filenames
- 🔐 **Secure Authentication** - OAuth 2.0 with automatic token refresh
- 📁 **CSV Export** - Export subtitle data for external processing
- ⚡ **Error Handling** - Robust error handling with detailed feedback

## 📋 Requirements

### System Requirements
- Python 3.7 or higher
- Active internet connection
- YouTube channel with videos and **admin/owner rights**

### Python Dependencies
```bash
pip install pandas colorama google-api-python-client google-auth-oauthlib google-auth
```

### API Requirements
- Google Cloud Console project
- YouTube Data API v3 enabled
- OAuth 2.0 credentials (client_secrets.json)
- **Channel admin/owner permissions** (required for subtitle management)

## 🛠️ Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/youtube-subtitles-manager.git
cd youtube-subtitles-manager
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup Google API credentials**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Download the credentials file as `client_secrets.json`

4. **Create configuration file**
```json
{
  "channels": {
    "main_channel": "UC1234567890abcdef",
    "secondary_channel": "UC0987654321fedcba"
  }
}
```

## 📖 Usage

### Show Help
```bash
python yousubv5.py
```

### Basic Command Structure
```bash
python yousubv5.py --channel <channel_nickname> <command>
```

## 🔧 Commands

### 📥 Download - Create Processing File
Generate a detailed CSV file with all subtitle information for batch processing.

```bash
python yousubv5.py --channel main_channel download
```
**Output:** `captions_main_channel.csv`

### 📊 Report - Generate Channel Report
Create a human-readable report showing subtitle availability across all videos.

```bash
python yousubv5.py --channel main_channel report
```
**Output:** `report_main_channel.csv`

### ⚙️ Process - Batch Operations
Process multiple subtitle operations from a CSV file.

```bash
python yousubv5.py --channel main_channel process --csv-path captions_main_channel.csv
```

**CSV Format:**
| video_id | video_title | caption_id | language | action | file_path |
|----------|-------------|------------|----------|--------|-----------|
| dQw4w9WgXcQ | Sample Video | - | en | UPLOAD | ./subs/video_en.srt |
| dQw4w9WgXcQ | Sample Video | cap124 | es | UPDATE | ./subs/video_es.srt |
| dQw4w9WgXcQ | Sample Video | cap125 | fr | DELETE | - |

**Actions:**
- `UPLOAD` - Upload new subtitle file
- `UPDATE` - Replace existing subtitle file  
- `DELETE` - Remove subtitle track

### 🚀 Upload - Single File Upload
Upload a single subtitle file to a specific video.

```bash
python yousubv5.py --channel main_channel upload --video-id dQw4w9WgXcQ --language en --file-path ./subtitles/video_en.srt
```

### 🎯 Smart Upload - Automatic Processing
Upload multiple files by parsing filenames (format: `VIDEOID_LANGUAGE.ext`).

```bash
python yousubv5.py --channel main_channel smart-upload dQw4w9WgXcQ_en.srt dQw4w9WgXcQ_es.srt
```

**File Naming Convention:**
- Format: `VIDEO_ID_LANGUAGE.extension`
- Example: `dQw4w9WgXcQ_en.srt`, `dQw4w9WgXcQ_es.srt`

## 🐛 Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Configuration file not found` | Missing config.json | Create config.json with channel info |
| `client_secrets.json not found` | Missing OAuth credentials | Download credentials from Google Cloud Console |
| `No valid token` | Authentication required | Follow browser authentication |
| `HTTP error 403` | Insufficient permissions | Verify admin/owner rights to channel |
| `HTTP error 404` | Invalid video/caption ID | Check video ID exists and accessible |
| `Invalid filename format` | Wrong naming for smart upload | Use format: `VIDEOID_LANGUAGE.ext` |
| `quotaExceeded` | Daily API limit reached | Wait 24 hours or request quota increase |

### Common Issues

**🔐 Authentication Problems**
- Ensure you have **admin or owner rights** to the YouTube channel
- Check you're logged in with the correct Google account
- Delete token file and re-authenticate if needed

**📁 File Processing Issues**
- Ensure CSV files are UTF-8 encoded
- Check file paths are correct and files exist
- Break large batches into smaller chunks

## 📊 API Quota Limits

### Daily Quotas (Default: 10,000 units)

| Command | Cost per Operation | Max Operations/Day |
|---------|-------------------|-------------------|
| `download` | 1 unit per video | ~10,000 videos |
| `report` | 1 unit per video | ~10,000 videos |
| `upload` | 400 units | ~25 uploads |
| `update` | 450 units | ~22 updates |
| `delete` | 50 units | ~200 deletions |

### 💡 Quota Tips
- Monitor usage in Google Cloud Console
- Use batch operations for efficiency
- Schedule large operations during off-peak hours
- Request quota increase if needed

## 📁 File Structure

```
youtube-subtitles-manager/
├── yousubv5.py
├── config.json
├── client_secrets.json
├── requirements.txt
├── README.md
└── subtitles/
    ├── VIDEO_ID_en.srt
    ├── VIDEO_ID_es.srt
    └── VIDEO_ID_fr.srt
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Important Notes

- **You must have admin or owner rights** to the YouTube channel to manage subtitles
- Always test with a few videos before running large batch operations
- Keep backups of your subtitle files
- Monitor your API quota usage regularly
- Respect YouTube's terms of service

## 🆘 Support

If you encounter issues:
1. Check the troubleshooting table above
2. Review your API quotas in Google Cloud Console
3. Verify you have proper channel permissions
4. Open an issue on GitHub with detailed error information

---

**Made with ❤️ for content creators worldwide**
