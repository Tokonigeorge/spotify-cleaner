import questionary
from rich.console import Console

console = Console()

def select_playlists_interactive(playlists):
    """
    Displays an interactive checklist for the user to select playlists.

    Args:
        playlists (list): A list of playlist objects from the Spotify API.

    Returns:
        list: A list of selected playlist objects, or an empty list if none selected.
    """
    if not playlists:
        return []

    # Format the playlist choices for the prompt
    choices = [
        {
            "name": (
                f"{p.get('name', 'Untitled Playlist')} "
                f"({p.get('tracks', {}).get('total', 0)} tracks, "
                f"Owner: {p.get('owner', {}).get('display_name', 'N/A')})"
            ),
            "value": p,
            "checked": False,
        }
        for p in playlists
    ]

    try:
        selected_playlists = questionary.checkbox(
            "Use [↑/↓] to navigate, [space] to select/deselect, [enter] to confirm.",
            choices=choices,
            validate=lambda a: True if len(a) > 0 else "You must select at least one playlist.",
        ).ask()

        return selected_playlists if selected_playlists else []
    except KeyboardInterrupt:
        # Catches Ctrl+C and exits gracefully
        console.print("\nOperation cancelled by user.", style="yellow")
        return [] 