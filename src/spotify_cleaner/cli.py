import re
import click
from rich.console import Console
from rich.progress import track
from rich.table import Table
import functools

from . import auth
from . import interactive
from .spotify_client import SpotifyClient

console = Console()

def _apply_filters_to_playlists(playlists, client, name, owner, is_collaborative, empty, no_description):
    """Applies a series of filters to a list of playlist objects."""
    
    filtered_playlists = list(playlists)

    if name:
        try:
            name_re = re.compile(name, re.IGNORECASE)
            filtered_playlists = [p for p in filtered_playlists if name_re.search(p.get('name', ''))]
        except re.error as e:
            console.print(f"[bold red]Invalid regex for --name: {e}[/bold red]")
            # Return an empty list or raise an exception to stop processing
            return []
    
    if owner:
        current_user = client.get_current_user()
        if not current_user:
            return [] # Error already printed by client
        current_user_id = current_user['id']

        if owner.lower() == 'me':
            filtered_playlists = [p for p in filtered_playlists if p.get('owner', {}).get('id') == current_user_id]
        elif owner.lower() == 'not-me':
            filtered_playlists = [p for p in filtered_playlists if p.get('owner', {}).get('id') != current_user_id]
        else:
            filtered_playlists = [p for p in filtered_playlists if p.get('owner', {}).get('id') == owner]
    
    if is_collaborative is not None:
            filtered_playlists = [p for p in filtered_playlists if p.get('collaborative') == is_collaborative]
    
    if empty:
        filtered_playlists = [p for p in filtered_playlists if p.get('tracks', {}).get('total', -1) == 0]

    if no_description:
        filtered_playlists = [p for p in filtered_playlists if not p.get('description')]
        
    return filtered_playlists

def add_filter_options(f):
    """A decorator to add all the common filter options to a command."""
    options = [
        click.option('--name', help='Filter playlists where the name matches a regex pattern.'),
        click.option('--owner', help="Filter by owner's user ID. Use 'me' for your playlists or 'not-me' for others."),
        click.option('--collaborative', 'is_collaborative', is_flag=True, default=None, help='Target only collaborative playlists.'),
        click.option('--not-collaborative', 'is_collaborative', flag_value=False, help='Target only non-collaborative playlists.'),
        click.option('--empty', is_flag=True, help='Target only playlists with zero tracks.'),
        click.option('--no-description', is_flag=True, help='Target playlists that have no description.'),
    ]
    return functools.reduce(lambda x, opt: opt(x), reversed(options), f)

@click.group(invoke_without_command=True)
@click.option('--re-auth', is_flag=True, help="Force re-authentication, ignoring any stored credentials.")
@click.pass_context
def main(ctx, re_auth):
    """
    A CLI tool to bulk-unfollow Spotify playlists.
    If no command is specified, defaults to 'list'.
    """
    ctx.ensure_object(dict)
    
    access_token = auth.get_access_token(force_reauth=re_auth)
    if not access_token:
        console.print("Authentication failed. Exiting.", style="bold red")
        raise click.Abort()

    ctx.obj['client'] = SpotifyClient(access_token)
    
    # If no subcommand is given, run `list` by default
    if ctx.invoked_subcommand is None:
        ctx.invoke(list_playlists)

@main.command('list')
@click.option('--page', default=1, help='The page number to display.', type=int)
@click.option('--limit', default=50, help='The number of playlists to display per page.', type=int)
@add_filter_options
@click.pass_context
def list_playlists(ctx, page, limit, **filters):
    """
    Lists your playlists, with optional filtering and pagination.
    """
    client = ctx.obj['client']
    
    filters_provided = any(filters.values())

    if filters_provided:
        # If filtering, we must fetch all playlists first, then filter and paginate manually
        all_playlists = client.get_all_playlists()
        playlists_to_display = _apply_filters_to_playlists(all_playlists, client, **filters)
        total = len(playlists_to_display)
        start_index = (page - 1) * limit
        end_index = start_index + limit
        paged_playlists = playlists_to_display[start_index:end_index]
    else:
        # Otherwise, use the efficient API-based pagination
        data = client.get_playlists_page(page, limit)
        if not data:
            console.print("Could not fetch playlists.", style="red")
            return
        paged_playlists = data.get('items', [])
        total = data.get('total', 0)

    if not paged_playlists:
        console.print("No playlists found matching your criteria.", style="yellow")
        return

    table = Table(title="Your Spotify Playlists")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("ID", style="magenta")
    table.add_column("Owner", style="green")
    table.add_column("Tracks", justify="right", style="green")
    table.add_column("Collaborative", justify="center")
    table.add_column("Public", justify="center")

    for p in paged_playlists:
        table.add_row(
            p['name'],
            p['id'],
            p.get('owner', {}).get('display_name', 'N/A'),
            str(p.get('tracks', {}).get('total', 0)),
            "✅" if p.get('collaborative') else "❌",
            "✅" if p.get('public') else "❌",
        )
    
    console.print(table)
    
    # Calculate offset for display message
    offset = (page - 1) * limit
    console.print(f"Showing playlists [bold]{offset + 1}-{offset + len(paged_playlists)}[/bold] of [bold]{total}[/bold].")

@main.command()
@add_filter_options
@click.option('--dry-run', is_flag=True, help="Show which playlists would be unfollowed without actually doing it.")
@click.option('-y', '--yes', is_flag=True, help="Skip the confirmation prompt before unfollowing.")
@click.pass_context
def clean(ctx, dry_run, yes, **filters):
    """
    Unfollow playlists based on specified filters or via an interactive prompt.
    """
    client = ctx.obj['client']
    playlists_to_unfollow = []
    
    # Check if any filter flags have been used
    filters_provided = any(filters.values())

    all_playlists = client.get_all_playlists()

    # If no filters are provided, enter interactive mode
    if not filters_provided:
        console.print("[bold]Entering interactive mode...[/bold]")
        playlists_to_unfollow = interactive.select_playlists_interactive(all_playlists)
    else:
        # Otherwise, apply the given filters
        playlists_to_unfollow = _apply_filters_to_playlists(all_playlists, client, **filters)

    if not playlists_to_unfollow:
        console.print("No playlists selected or found matching the criteria.", style="yellow")
        return

    console.print("\nThe following playlists will be unfollowed:", style="bold yellow")
    for p in playlists_to_unfollow:
        console.print(f" - [cyan]{p['name']}[/cyan] (ID: {p['id']})")
    
    if dry_run:
        console.print("\n[bold]--dry-run enabled. No playlists will be unfollowed.[/bold]")
        return
        
    if not yes:
        if not click.confirm(f"\nAre you sure you want to unfollow {len(playlists_to_unfollow)} playlists?"):
            console.print("Operation cancelled.")
            return
            
    # Perform the unfollow operation
    for p in track(playlists_to_unfollow, description="Unfollowing playlists..."):
        client.unfollow_playlist(p['id'])
        
    console.print(f"\n[bold green]Successfully unfollowed {len(playlists_to_unfollow)} playlists.[/bold green]")

@main.command()
@click.pass_context
def test_auth(ctx):
    """
    Tests authentication by fetching the current user's profile.
    """
    console.print("Attempting to fetch user profile...", style="bold blue")
    client = ctx.obj['client']
    
    # This method handles the API call and any potential errors
    user_data = client.get_current_user()

    if user_data:
        console.print("\n[bold green]Authentication test successful! Fetched user data:[/bold green]")
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column()
        table.add_row("Display Name:", user_data.get('display_name', 'N/A'))
        table.add_row("ID:", user_data.get('id', 'N/A'))
        table.add_row("Email:", user_data.get('email', 'N/A (permission not granted)'))
        profile_url = user_data.get('external_urls', {}).get('spotify')
        if profile_url:
            table.add_row("Profile URL:", f"[link={profile_url}]{profile_url}[/link]")
        console.print(table)
    else:
        console.print("\n[bold red]Authentication test failed. Could not fetch user data.[/bold red]")

if __name__ == "__main__":
    main() 