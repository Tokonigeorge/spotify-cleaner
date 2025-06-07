# Project Plan: Spotify Cleaner

This document outlines the plan for creating "Spotify Cleaner," a command-line tool for bulk-deleting Spotify playlists.

## 1. Core Concept

A standalone, cross-platform command-line interface (CLI) application that allows users to mass-delete (or more accurately, unfollow) Spotify playlists based on specified criteria. It will use the official Spotify Web API, making it robust against changes to Spotify's web or desktop clients.

## 2. Authentication

Authentication will follow Spotify's **Authorization Code Flow (OAuth 2.0)**.

1.  **App Registration**: The developer must first register an application on the [Spotify for Developers Dashboard](https://developer.spotify.com/dashboard/) to get a `Client ID` and `Client Secret`. A `Redirect URI` must also be set (e.g., `http://localhost:8888/callback`).
2.  **First-Time-Use**:
    - The script detects it has no saved authorization token.
    - It constructs and prints a unique authorization URL to the console.
    - The user must open this URL in their browser, log into Spotify, and grant the application permissions.
    - Spotify redirects the user to the `Redirect URI`.
3.  **Token Exchange**:
    - The script will run a temporary local web server to "catch" this redirect and extract an `authorization_code`.
    - The script immediately exchanges this code with the Spotify API (using the `Client ID` and `Client Secret`) for an `access_token` and a `refresh_token`.
4.  **Secure Storage**:
    - The `refresh_token` must be stored securely on the user's machine. **This should not be a plain text file.** The application should use the operating system's native secret storage (e.g., Keychain on macOS, Credential Manager on Windows, Secret Service on Linux).
    - On subsequent runs, the script will use the stored `refresh_token` to silently get a new `access_token` without requiring user interaction.

## 3. Command-Line Interface (CLI) Design

The primary interface will be through terminal commands and flags.

**Base Command**: `spotify-cleaner`

### Arguments & Flags:

- #### Filtering

  - `--name <regex>`: Filter playlists where the name matches the given regular expression.
  - `--owner <user_id>`: Filter by playlist owner. Could include a special value like `--not-my-playlists` to target playlists owned by others.
  - `--collaborative`: Target only collaborative playlists.
  - `--empty`: Target only playlists with zero tracks.
  - `--created-before <date>`: Target playlists created before a specified date (YYYY-MM-DD).
  - `--no-description`: Target playlists that have no description.

- #### Safety & Interaction

  - `--interactive`: (Default behavior) Fetch and display a list of all user playlists. The user can then manually select which ones to delete using keyboard navigation (e.g., arrow keys to move, spacebar to select).
  - `--dry-run`: **This is a critical safety feature.** List the playlists that _would_ be deleted based on the filter flags, but do not perform the deletion. This allows users to verify their filters.
  - `--yes` or `-y`: Skip the final "Are you sure?" confirmation prompt. For confident power users.

- #### Authentication
  - `--re-auth`: Force the script to re-run the full browser-based authentication flow, overwriting any saved credentials.

### Example Usage:

```bash
# Preview which playlists with "old" in the name would be deleted
spotify-cleaner --name "old" --dry-run

# Interactively choose from all collaborative playlists to delete
spotify-cleaner --collaborative

# Delete all empty playlists created before 2020 without a confirmation prompt
spotify-cleaner --empty --created-before 2020-01-01 -y
```

## 4. Terminal User Experience (UX)

The CLI should be user-friendly with clear text and a clean layout. Use of libraries like `rich` (Python) or `inquirer`/`chalk` (Node.js) is recommended.

#### Example: Interactive Mode

```
Use [↑/↓] to navigate, [space] to select, [a] to toggle all, [enter] to confirm.

Playlists to delete:

[x] Old Workout Mix
[ ] Liked from Radio
[x] 90s Rock
[x] temp playlist
[ ] Roadtrip 2022

(3 selected)
```

#### Example: Deletion Confirmation & Progress

```
The following 3 playlists will be permanently unfollowed:
 - Old Workout Mix
 - 90s Rock
 - temp playlist

Are you sure? (y/N) y

Unfollowing...
[■■■■■■■■■■■■■■■■■■■■■■■■■] 100% | 3/3 | Done!
```

## 5. Important Technical Considerations

- **"Delete" vs. "Unfollow"**: The Spotify API action is to "unfollow" a playlist. For playlists the user owns, this is effectively a delete. For playlists they follow, it removes it from their library. The tool's language should be precise about this. "Unfollow" is the more accurate term.
- **API Rate Limiting**: The script must gracefully handle Spotify's API rate limits. If a "429 Too Many Requests" error is received, the script should pause and retry after the duration specified in the `Retry-After` header.
- **Error Handling**: Network errors, invalid tokens, or permissions issues should be caught and reported clearly to the user.
- **Irrecoverability**: Deletion/unfollowing is permanent. This must be communicated clearly through warnings and confirmation prompts. The `--dry-run` flag is the primary tool to prevent mistakes.
- **Pagination**: API calls that return lists (like fetching playlists) are paginated. The script must handle this by making subsequent requests to fetch all pages of results.
