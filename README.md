# Spotify Cleaner

A command-line tool to bulk-unfollow Spotify playlists based on specified criteria, with filtering and a safe interactive mode.

This project was born out of necessity. I somehow created over a thousand unwanted playlists on my account while working on another project that interacted with the Spotify API, and I didn't want to delete them one-by-one, this was built to solve the problem for myself and anyone else who might need it.

## Features

- **Interactive Mode**: A user-friendly checklist for manually selecting playlists to unfollow.
- **Powerful Filtering**: List or unfollow playlists programmatically based on:
  - Name (with regex support)
  - Owner (you, someone else, or a specific user ID)
  - Collaborative status
  - Empty playlists (zero tracks)
  - Playlists with no description
- **Safety First**:
  - A `--dry-run` mode to preview what will be unfollowed without making changes.
  - A final confirmation prompt for all destructive operations (can be skipped with `-y`).
- **Secure**: Your Spotify credentials are never hardcoded. They are loaded from a local `.env` file, and your authentication token is stored securely in your operating system's native keychain.

## Installation

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/your-username/spotify-cleaner.git
    cd spotify-cleaner
    ```

2.  **Create a Virtual Environment**
    It is highly recommended to install the tool in a virtual environment.

    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**
    This command installs the project and all its required libraries.
    ```bash
    pip install -e .
    ```

## Configuration

Before you can use the tool, you need to provide it with your Spotify API credentials.

1.  **Get Credentials**:

    - Go to the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/).
    - Click `Create app`.
    - Give your app a name and description.
    - Now, in your app's settings, find the **Client ID** and **Client Secret**.
    - Add a **Redirect URI**: `http://127.0.0.1:8888/callback`. Make sure to click `Add` and then `Save`.

2.  **Create a `.env` file**:
    In the root of the project directory, create a file named `.env`. Copy and paste the following into it, replacing the placeholder values with your actual credentials from the developer dashboard.
    ```ini
    SPOTIFY_CLIENT_ID="YOUR_CLIENT_ID"
    SPOTIFY_CLIENT_SECRET="YOUR_CLIENT_SECRET"
    ```
    This file is included in `.gitignore`, so your secrets will never be committed to your repository.

## Usage

The first time you run any command, your browser will open and ask you to log in to Spotify and authorize the application. After that, your credentials will be stored securely for future use.

**Default Command: List Playlists**

Running `spotify-cleaner` with no command defaults to listing your playlists in a paginated table. You can use filters to narrow down the list.

```bash
# List the first page of your playlists
spotify-cleaner

# List page 3
spotify-cleaner list --page 3

# List all your empty, non-collaborative playlists
spotify-cleaner list --owner me --empty --not-collaborative
```

**Clean Command: Unfollow Playlists**

The `clean` command is used to unfollow playlists.

### Interactive Mode

For safe, manual cleaning, run `clean` with no filters. This will open an interactive checklist of all your playlists.

```bash
spotify-cleaner clean
```

Use `↑/↓` to navigate, `space` to select, and `enter` to confirm.

### Filter Mode

Unfollow playlists automatically by applying one or more filters.

**Core Flags:**

- `--dry-run`: **(Recommended)** Preview which playlists match your filters without unfollowing them.
- `-y`, `--yes`: Skip the "Are you sure?" confirmation prompt.

**Filter Flags:**

- `--name <regex>`: Filter by name using a regular expression.
- `--owner <id>`: Filter by owner. Use `me`, `not-me`, or a specific Spotify User ID.
- `--collaborative` / `--not-collaborative`: Target based on collaborative status.
- `--empty`: Target only playlists with 0 tracks.
- `--no-description`: Target only playlists with no description text.

### Examples

**Dry Runs (Safe Previews):**

```bash
# Preview which playlists with "old" in the name would be unfollowed
spotify-cleaner clean --name "old" --dry-run

# Preview all of your empty, non-collaborative playlists
spotify-cleaner clean --owner me --empty --not-collaborative --dry-run
```

**Actual Unfollowing:**

```bash
# Unfollow all playlists with a name that starts with "Temp" (will ask for confirmation)
spotify-cleaner clean --name "^Temp"

# Unfollow all empty playlists you don't own, skipping the confirmation prompt
spotify-cleaner clean --owner not-me --empty --yes
```

**Authentication Management**

- `--re-auth`: Add this flag to any command to force a new browser-based login, overwriting your stored token.

  ```bash
  spotify-cleaner --re-auth list
  ```

- `test-auth`: A utility command to check if your authentication is working correctly.
  ```bash
  spotify-cleaner test-auth
  ```

---

Built with ❤️ and Python.
