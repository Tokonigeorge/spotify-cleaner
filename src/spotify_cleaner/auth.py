import base64
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import keyring
import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

# --- Spotify API Configuration ---
# The Client ID and Secret are loaded from a .env file.
# Create a .env file in the root directory with your credentials.
# EXAMPLE:
# SPOTIFY_CLIENT_ID="YOUR_CLIENT_ID"
# SPOTIFY_CLIENT_SECRET="YOUR_CLIENT_SECRET"
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-read-email playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative"
KEYRING_SERVICE_NAME = "spotify-cleaner"

# --- Authentication State ---
# This global variable will hold the authorization code received from Spotify.
# This is a simple way to pass the code from the HTTP server to the main auth flow.
authorization_code = None

console = Console()


class CallbackHandler(BaseHTTPRequestHandler):
    """
    A simple HTTP request handler to catch the OAuth 2.0 callback from Spotify.
    """
    def do_GET(self):
        """
        Handles the GET request from Spotify's redirect.
        Extracts the authorization code and shuts down the server.
        """
        global authorization_code
        # Parse the query parameters from the request URL
        query = urlparse(self.path).query
        params = parse_qs(query)

        # Send a 200 OK response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        if "code" in params:
            authorization_code = params["code"][0]
            # Display a friendly message in the user's browser
            self.wfile.write(b"<html><body>")
            self.wfile.write(b"<h1>Authentication Successful!</h1>")
            self.wfile.write(b"<p>You can close this window now.</p>")
            self.wfile.write(b"</body></html>")
        else:
            # Handle the case where there's an error
            error = params.get("error", ["Unknown error"])[0]
            self.wfile.write(b"<html><body>")
            self.wfile.write(f"<h1>Authentication Failed:</h1><p>{error}</p>".encode("utf-8"))
            self.wfile.write(b"</body></html>")
            console.log(f"[bold red]Authentication failed. Error: {error}[/bold red]")

        # Stop the server
        # This needs to be done in a separate thread to avoid a deadlock
        import threading
        killer = threading.Thread(target=self.server.shutdown)
        killer.start()

def _perform_auth_flow():
    """
    Handles the full browser-based OAuth 2.0 authentication flow.
    """
    # Check if the user has filled in their credentials
    if not CLIENT_ID or not CLIENT_SECRET:
        console.print("[bold red]Error: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in your .env file.[/bold red]")
        return None

    # Step 1: Construct the authorization URL
    auth_url = (
        "https://accounts.spotify.com/authorize?"
        f"client_id={CLIENT_ID}&"
        "response_type=code&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope={SCOPES}"
    )

    # Step 2: Open the URL and start the local server
    console.print("Your browser should open for you to authorize the application.")
    console.print("If it doesn't, please open this URL manually:")
    console.print(f"[link={auth_url}]{auth_url}[/link]")
    webbrowser.open(auth_url)

    server_address = ('127.0.0.1', 8888)
    httpd = HTTPServer(server_address, CallbackHandler)
    httpd.serve_forever()

    if not authorization_code:
        console.print("[bold red]Authentication failed. Could not get authorization code.[/bold red]")
        return None

    # Step 3: Exchange the authorization code for an access token
    token_url = "https://accounts.spotify.com/api/token"
    auth_string = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_string}"}
    payload = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
    }
    response = requests.post(token_url, headers=headers, data=payload)
    token_info = response.json()

    if "refresh_token" in token_info:
        # Step 4: Securely store the refresh token
        keyring.set_password(KEYRING_SERVICE_NAME, "refresh_token", token_info["refresh_token"])
        console.print("[green]Successfully authenticated and stored refresh token.[/green]")
        return token_info.get("access_token")
    else:
        console.print("[bold red]Failed to get refresh token.[/bold red]")
        console.print(token_info)
        return None

def _refresh_access_token(refresh_token):
    """
    Uses a refresh token to get a new access token.
    """
    token_url = "https://accounts.spotify.com/api/token"
    auth_string = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_string}"}
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    response = requests.post(token_url, headers=headers, data=payload)
    token_info = response.json()

    if "access_token" in token_info:
        # Note: Spotify may or may not return a new refresh token.
        # If it does, we should update our stored one.
        if "refresh_token" in token_info:
            keyring.set_password(KEYRING_SERVICE_NAME, "refresh_token", token_info["refresh_token"])
        return token_info["access_token"]
    else:
        console.print("[bold yellow]Could not refresh access token.[/bold yellow]")
        return None

def get_access_token(force_reauth=False):
    """
    Gets an access token, either from the keychain or by re-authenticating.
    This is the main function the app should call to get a token.
    """
    if force_reauth:
        console.print("Forcing re-authentication...")
        return _perform_auth_flow()

    refresh_token = keyring.get_password(KEYRING_SERVICE_NAME, "refresh_token")
    if refresh_token:
        console.print("Found refresh token. Attempting to get new access token...")
        access_token = _refresh_access_token(refresh_token)
        if access_token:
            console.print("[green]Successfully got new access token.[/green]")
            return access_token
        else:
            console.print("Failed to use refresh token. Starting full auth flow...")
            return _perform_auth_flow()
    else:
        console.print("No refresh token found. Starting first-time authentication...")
        return _perform_auth_flow()

def clear_credentials():
    """
    Removes the stored refresh token from the system's keychain.
    """
    try:
        keyring.delete_password(KEYRING_SERVICE_NAME, "refresh_token")
        console.print("[green]Stored credentials have been cleared.[/green]")
    except keyring.errors.PasswordNotFoundError:
        # This is expected if the user has never authenticated or already cleared them
        console.print("[green]No stored credentials to clear.[/green]")
    except keyring.errors.NoKeyringError:
        console.print("[yellow]No keyring backend found. Nothing to clear.[/yellow]")
    except Exception as e:
        console.print(f"[red]An unexpected error occurred while clearing credentials: {e}[/red]") 