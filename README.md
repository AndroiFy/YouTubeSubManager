# YouTube Subtitles Manager

> 🎬 A powerful Python tool for managing YouTube video subtitles across multiple channels using a simple, project-based workflow.

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![YouTube API](https://img.shields.io/badge/YouTube%20API-v3-red.svg)](https://developers.google.com/youtube/v3)

## ✨ Core Features

- 📁 **Project-Based Workflow**: Manage all your subtitles for a channel in a simple project folder. No more messy CSVs!
- 🔄 **Smart Syncing**: Automatically detects local changes (new, updated, deleted subtitles) and syncs them with YouTube.
- ⚡ **API Quota Protection**: Built-in caching and quota tracking to prevent you from exceeding YouTube's daily API limits.
- 📺 **Multi-Channel Support**: Manage subtitles for all your YouTube channels from one place.
- 🎨 **Beautiful Interface**: Colorful terminal output with emojis for a clear and enjoyable experience.
- 🔐 **Secure Authentication**: Uses OAuth 2.0 with automatic token refresh to keep your account secure.

---

## 📋 Table of Contents

1.  [How it Works](#-how-it-works)
2.  [Installation and Setup](#-installation-and-setup)
    - [Step 1: Clone the Repository](#step-1-clone-the-repository)
    - [Step 2: Install Dependencies](#step-2-install-dependencies)
    - [Step 3: Configure Google Cloud & YouTube API](#step-3-configure-google-cloud--youtube-api)
    - [Step 4: Create the Configuration File](#step-4-create-the-configuration-file)
3.  [Usage](#-usage)
    - [Command 1: `project`](#command-1-project-create-a-new-project)
    - [Command 2: `sync`](#command-2-sync-your-local-changes)
4.  [Other Commands](#-other-commands)
5.  [Troubleshooting and Errors](#-troubleshooting-and-errors)
6.  [API Quota Management](#-api-quota-management)
7.  [File Structure](#-file-structure)

---

## 🤔 How it Works

This tool simplifies subtitle management by moving away from complex spreadsheets and towards a simple, folder-based system.

**The workflow is easy:**

1.  **Create a Project**: You run the `project` command once for a channel. This creates a new folder (e.g., `projects/my-channel/`) and downloads a `subtitles.json` file, which acts as a master list of all your videos and their subtitles.
2.  **Add & Edit Subtitles**: You add your subtitle files (e.g., `.srt` files) to the project folder. To update a subtitle, you just edit the file. To delete one, you delete the file. The filename format is simple: `VIDEOID_LANGUAGE.srt`.
3.  **Sync Your Changes**: You run the `sync` command. The tool automatically compares the files in your project folder to the `subtitles.json` manifest and the live data on YouTube. It then intelligently performs all the necessary uploads, updates, and deletions to get everything in sync.

---

## ⚙️ Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-username/youtube-subtitles-manager.git
cd youtube-subtitles-manager
```

### Step 2: Install Dependencies

Make sure you have Python 3.7+ installed. Then, install the required packages:

```bash
pip install -r requirements.txt
```

### Step 3: Configure Google Cloud & YouTube API

This is the most important step. To use the tool, you need to give it permission to access your YouTube account.

1.  **Create a Google Cloud Project**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Click the project dropdown in the top-left corner and click **New Project**.
    *   Give it a name (e.g., "YouTube Subtitle Manager") and click **Create**.

2.  **Enable the YouTube Data API v3**:
    *   In your new project, navigate to the **APIs & Services > Library** page.
    *   Search for "YouTube Data API v3" and click on it.
    *   Click the **Enable** button.

3.  **Configure the OAuth Consent Screen**:
    *   Navigate to **APIs & Services > OAuth consent screen**.
    *   Choose **External** and click **Create**.
    *   Fill in the required fields:
        *   **App name**: "YouTube Subtitle Manager" (or any name you prefer).
        *   **User support email**: Your email address.
        *   **Developer contact information**: Your email address.
    *   Click **Save and Continue**.
    *   On the "Scopes" page, click **Add or Remove Scopes**. Find the scope for the YouTube Data API v3 with the path `.../auth/youtube.force-ssl`, check the box, and click **Update**.
    *   Click **Save and Continue**.
    *   On the "Test users" page, click **Add Users** and add the Google account that manages your YouTube channel. This is very important!
    *   Click **Save and Continue** and then **Back to Dashboard**.

4.  **Create OAuth 2.0 Credentials**:
    *   Navigate to **APIs & Services > Credentials**.
    *   Click **Create Credentials** and select **OAuth client ID**.
    *   For **Application type**, select **Desktop app**.
    *   Give it a name (e.g., "Subtitle Manager Credentials") and click **Create**.
    *   A window will pop up. Click **Download JSON**.
    *   **Rename the downloaded file to `client_secrets.json`** and place it in the root directory of this project.

### Step 4: Create the Configuration File

1.  **Find your Channel ID**:
    *   Go to your YouTube channel page.
    *   Click on your profile picture in the top right and go to **Settings**.
    *   In the left menu, click **Advanced settings**.
    *   You will see your **Channel ID** (it starts with `UC...`). Copy it.

2.  **Create `config.json`**:
    *   In the root of the project, create a file named `config.json`.
    *   Add your channel(s) using a friendly nickname. This allows you to easily manage multiple channels.

    ```json
    {
      "channels": {
        "my-main-channel": "UCxxxxxxxxxxxxxxxxxxxxxx",
        "another-channel": "UCyyyyyyyyyyyyyyyyyyyyyy"
      }
    }
    ```

You are now ready to use the tool!

---

## 📖 Usage

The tool is run from your terminal.

### Command 1: `project` (Create a New Project)

This command creates a new project folder for a channel. You only need to run this **once** per channel.

```bash
python yousub.py --channel <channel_nickname> project <project_name>
```

-   `<channel_nickname>`: The nickname you defined in `config.json`.
-   `<project_name>`: A name for your project folder (e.g., "my-channel-subtitles").

**Example:**

```bash
python yousub.py --channel my-main-channel project main-channel-subs
```

This will create a `projects/main-channel-subs` directory and populate it with a `subtitles.json` file.

### Command 2: `sync` (Sync Your Local Changes)

This is the main command you will use. It scans your project folder for changes and syncs them with YouTube.

```bash
python yousub.py --channel <channel_nickname> sync <project_name>
```

**Example:**

```bash
python yousub.py --channel my-main-channel sync main-channel-subs
```

**How to Use the `sync` Workflow:**

1.  **To Add a New Subtitle**: Create a new `.srt` file inside your project folder (e.g., `projects/main-channel-subs/`). Name it `VIDEOID_LANGUAGE.srt`. Run the `sync` command.
2.  **To Update an Existing Subtitle**: Simply edit and save the existing `.srt` file in your project folder. Run the `sync` command.
3.  **To Delete a Subtitle**: Delete the `.srt` file from your project folder. Run the `sync` command.

---

## 📦 Other Commands

These are legacy commands or for one-off tasks.

| Command        | Description                                                  | Example                                                                                              |
| -------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| `upload`       | Uploads a single subtitle file to a specific video ID.       | `... upload --video-id dQw4w9WgXcQ --language en --file-path ./subs/video_en.srt`                     |
| `smart-upload` | Uploads multiple files by parsing filenames (`VIDEOID_LANG.ext`). | `... smart-upload dQw4w9WgXcQ_en.srt dQw4w9WgXcQ_es.srt`                                          |
| `report`       | Generates a wide, human-readable CSV report of all subtitles for a channel. | `... report`                                                                                         |
| `download`     | Generates a long CSV file of all subtitles for batch processing (legacy). | `... download`                                                                                       |

---

## 🐛 Troubleshooting and Errors

| Error Message                      | Meaning                                                              | Solution                                                                                                                              |
| ---------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `Configuration file not found`     | The `config.json` file is missing.                                   | Create `config.json` in the root directory and add your channel information.                                                          |
| `client_secrets.json not found`    | The OAuth credentials file is missing.                               | Follow [Step 3](#step-3-configure-google-cloud--youtube-api) to download the JSON file and rename it to `client_secrets.json`. |
| `No valid token` or `invalid_grant` | Authentication failed or token expired.                              | The tool will try to open a browser for you to re-authenticate. If it fails, delete the `token_... .json` file and try again.      |
| `HTTP error 403: ...`              | You don't have permission.                                           | Ensure you are a **Manager** or **Owner** of the YouTube channel. Verify you added the correct account as a "Test user" in the OAuth consent screen. |
| `HTTP error 404: ...`              | The video ID or caption ID was not found.                            | Double-check that the video ID in your filename is correct and that the video hasn't been deleted.                                 |
| `Project ... not found`            | The `subtitles.json` file for your project is missing.               | Run the `project` command first to create the project.                                                                                |
| `quotaExceeded`                    | You have used up your daily API quota.                               | Wait 24 hours for the quota to reset. The tool's caching helps prevent this, but it can still happen with many new uploads/updates. |

---

## 📊 API Quota Management

The YouTube API has a daily limit of **10,000 units**. This tool has two features to help you manage this:

1.  **Caching**: The tool automatically caches API responses for listing videos and subtitles in the `cache/` directory. If you run a command multiple times, it will use the local cache instead of the API, saving you quota points. The cache expires after 1 hour.
2.  **Quota Tracking**: The tool tracks the *estimated* cost of every API call you make during a session and prints a summary report at the end, so you know exactly how much quota you've used.

**API Call Costs:**

| Operation          | Estimated Cost |
| ------------------ | -------------- |
| Listing Videos     | 1 unit         |
| Listing Captions   | 50 units       |
| Uploading a Caption | 400 units      |
| Updating a Caption | 450 units      |
| Deleting a Caption | 50 units       |

---

## 📁 File Structure

```
youtube-subtitles-manager/
├── src/
│   ├── main.py
│   ├── youtube_api.py
│   ├── file_handler.py
│   ├── config.py
│   ├── cache.py
│   └── quota.py
├── projects/
│   └── <your_project_name>/
│       ├── subtitles.json
│       ├── VIDEOID1_en.srt
│       └── VIDEOID2_fr.srt
├── cache/
│   └── ... (cache files)
├── tests/
│   └── ... (test files)
├── yousub.py
├── config.json
├── client_secrets.json
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.