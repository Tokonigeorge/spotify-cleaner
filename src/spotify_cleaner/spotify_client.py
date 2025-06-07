import time
import requests
from rich.console import Console

API_BASE_URL = "https://api.spotify.com/v1/"

console = Console()

class SpotifyClient:
    """
    A client for interacting with the Spotify Web API.
    """
    def __init__(self, access_token):
        if not access_token:
            raise ValueError("Access token cannot be None.")
        self._access_token = access_token
        self._headers = {"Authorization": f"Bearer {self._access_token}"}
        self._user_data = None  # Cache for the current user's data

    def _request(self, method, endpoint, params=None, json=None, retries=3):
        """
        Makes a generic request to the Spotify API.
        Handles absolute URLs for pagination and rate limiting.
        """
        url = endpoint if endpoint.startswith("http") else API_BASE_URL + endpoint
        
        try:
            response = requests.request(method, url, headers=self._headers, params=params, json=json)
            
            # Handle rate limiting
            if response.status_code == 429 and retries > 0:
                retry_after = int(response.headers.get("Retry-After", 5))
                console.print(f"[bold yellow]Rate limited. Retrying in {retry_after} seconds...[/bold yellow]")
                time.sleep(retry_after)
                return self._request(method, endpoint, params=params, json=json, retries=retries - 1)

            response.raise_for_status()
            # Return JSON response if content exists, otherwise return None
            return response.json() if response.content else None
        
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]An error occurred with the request: {e}[/bold red]")
            return None

    def get_all_playlists(self):
        """
        Fetches all of the current user's playlists, handling pagination.
        """
        all_playlists = []
        # The endpoint for the current user's playlists
        url = "me/playlists"
        params = {"limit": 50}  # Get 50 playlists at a time, the maximum allowed

        with console.status("[bold green]Fetching all playlists...", spinner="dots") as status:
            while url:
                try:
                    data = self._request("GET", url, params=params)
                    if not data:
                        # Error occurred and was printed by _request, stop processing
                        break
                    
                    all_playlists.extend(data["items"])
                    # Get the URL for the next page of results, if it exists
                    url = data.get("next")
                    # Subsequent requests are full URLs, so params are not needed
                    params = None 
                    
                    status.update(f"[bold green]Fetching all playlists... Found {len(all_playlists)} playlists.")
                except requests.HTTPError as e:
                    console.print(f"[bold red]Error fetching playlists: {e}[/bold red]")
                    # Stop trying if there's an error
                    break
        
        return all_playlists

    def get_playlists_page(self, page=1, limit=50):
        """
        Fetches a single page of the user's playlists.
        """
        params = {
            "limit": limit,
            "offset": (page - 1) * limit
        }
        try:
            return self._request("GET", "me/playlists", params=params)
        except requests.HTTPError as e:
            console.print(f"[bold red]Error fetching playlists page: {e}[/bold red]")
            return None

    def unfollow_playlist(self, playlist_id):
        """
        Unfollows (deletes) a playlist.
        """
        try:
            self._request("DELETE", f"playlists/{playlist_id}/followers")
            return True
        except requests.HTTPError as e:
            console.print(f"[bold red]Error unfollowing playlist {playlist_id}: {e}[/bold red]")
            return False

    def get_current_user(self):
        """
        Gets the profile information for the current user. Caches the result.
        """
        if self._user_data is None:
            console.print("Fetching user profile...", style="dim")
            self._user_data = self._request("GET", "me")
        return self._user_data 