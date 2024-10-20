import click
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
import questionary
from git_wise.core.generator import CommitMessageGenerator
from git_wise.config import load_config, save_config, get_api_key
from git_wise.utils.git_utils import get_all_staged_diffs, get_current_repo_info, print_staged_changes
from git_wise.core.generator import AIProvider
import sys
from git_wise.utils.exceptions import GitWiseError
from git.exc import InvalidGitRepositoryError
from typing import List
import pyperclip
from rich.syntax import Syntax
import os
import tempfile
import traceback
from git_wise.models.git_models import Language, DetailLevel, Model

console = Console()
VERSION = "0.1.0"

@click.group()
@click.version_option(VERSION, '-v', '--version', message='Git-Wise Version: %(version)s')
@click.help_option('-h', '--help')
def cli():
    """
    Git-Wise: An intelligent Git commit message generator.
    
    Use 'git-wise COMMAND --help' for more information about specific commands.
    """
    pass

def configure_language(current_config):
    language_choice = questionary.select(
        "Select your default commit message language:",
        choices=[lang.value[0] for lang in Language],
        default=Language.ENGLISH.value[0]
    ).ask()
    
    selected_language = next(lang for lang in Language if lang.value[0] == language_choice)
    if selected_language == Language.CUSTOM:
        default_language = questionary.text(
            "Enter the language code (e.g., fr, de, es) or language name:",
            validate=lambda text: len(text) > 0
        ).ask()
    else:
        default_language = selected_language.value[1]
    
    current_config['default_language'] = default_language
    return current_config

def configure_detail_level(current_config):
    detail_level = questionary.select(
        "Select the detail level for commit messages:",
        choices=[level.value[0] for level in DetailLevel],
        default=DetailLevel.BRIEF.value[0]
    ).ask()
    selected_detail = next(level for level in DetailLevel if level.value[0] == detail_level)
    current_config['detail_level'] = selected_detail.value[1]
    return current_config

def configure_api_key(current_config):
    api_key = input("Enter your OpenAI API key (may be used for other AI providers in the future):").strip()
    while not api_key:
        print("API key cannot be empty, please re-enter.")
        api_key = input("Enter your OpenAI API key (may be used for other AI providers in the future):").strip()
    current_config['openai_api_key'] = api_key
    return current_config

def configure_model(current_config):
    model_choice = questionary.select(
        "Select the default model:",
        choices=[model.value[0] for model in Model],
        default=Model.GPT4O_MINI.value[0]
    ).ask()
    selected_model = next(model for model in Model if model.value[0] == model_choice)
    current_config['default_model'] = selected_model.value[1]
    return current_config

def configure_interactive(current_config):
    interactive = questionary.confirm(
        "Do you want to enable interactive mode by default?",
        default=True
    ).ask()
    current_config['interactive'] = interactive
    return current_config

def configure_unlimited_chunk(current_config):
    unlimited_chunk = questionary.confirm(
        "Do you want to enable unlimited chunk mode by default?",
        default=False
    ).ask()
    current_config['unlimited_chunk'] = unlimited_chunk
    return current_config

@cli.command()
def init():
    """Initialize or reconfigure Git-Wise"""
    config = load_config()
    
    if config:
        if questionary.confirm(
            "Git-Wise is already configured. Do you want to clear the settings and reconfigure?",
            default=False
        ).ask():
            config = {}
        else:
            console.print("[green]Keeping existing configuration.[/green]")
            return

    config = configure_language(config)
    config = configure_detail_level(config)
    config = configure_api_key(config)
    config = configure_model(config)
    config = configure_interactive(config)
    config = configure_unlimited_chunk(config)
    
    save_config(config)
    
    console.print(Panel.fit(
        "[green]Configuration saved successfully![/green]",
        title="Success",
        border_style="green"
    ))
    print_welcome_screen()

@cli.command()
@click.option('--language', '-l', help='Language option (default: language in config)')
@click.option(
    '--detail', '-d',
    type=click.Choice([level.value[1] for level in DetailLevel]),
    help='Commit message detail level'
)
# TODO: feature: split changes into multiple commits
# @click.option('--split', '-s', is_flag=True, help='Split changes into multiple commits')
@click.option('--use-author-key', '-a', is_flag=True, help='Use author\'s API key, but not work! because I am poor :(🫡😎🥹')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode, I will ask you to confirm the commit message and create the commit!')
@click.option('--unlimited-chunk', '-u', is_flag=True, help='Enable unlimited chunk mode for processing large changes')
def start(language, detail, use_author_key, interactive, unlimited_chunk):
    """Generate commit messages for staged changes"""
    try:
        console.print("[bold gray]Checking configuration...[/bold gray]")
        config = load_config()
        api_key = get_api_key(use_author_key)
        if not api_key:
            raise GitWiseError(
                "OpenAI API key not set. Please run 'git-wise init' to configure, "
                "or use --use-author-key option."
            )
        
        generator = CommitMessageGenerator(AIProvider.OPENAI, model=config.get('default_model'), unlimited_chunk=config.get('unlimited_chunk', False))
        
        language = language or config.get('default_language', 'en')
        detail = detail or config.get('detail_level', 'brief')
        interactive = interactive or config.get('interactive', False)
        unlimited_chunk = unlimited_chunk or config.get('unlimited_chunk', False)
        console.print("[bold green]Checking configuration success![/bold green]")
        
        console.print("[bold]Analyzing staged changes...[/bold]")
        diffs = get_all_staged_diffs()
        if not diffs:
            raise GitWiseError("No staged files found. Stage your changes using 'git add' first.")
        
        changes: List[List[str]] = []
        for value in diffs.values():
            if isinstance(value, dict):
                changes.append([v for v in value.values()])
            elif isinstance(value, list):
                changes.append(value)
            else:
                changes.append([value])
                
        console.print("[bold green]Staged changes found![/bold green]")
        console.print("[bold]Getting current repository information...[/bold]")
        repo_info = get_current_repo_info()
        console.print(Text(f"repository information found.repo info", style="green", justify="left"))
        # if split:
        if False:
            pass
        else:
            changes_str = "\n".join(["\n".join(change) for change in changes])
            
            console.print("[bold]Generating commit message by AI...[/bold]")
            commit_message, token = generator.generate_commit_message(changes_str, language, detail, repo_info)
            display_commit_message(commit_message, token, interactive)
            
            if interactive:
                if questionary.confirm("Do you want to use this commit message?").ask():
                    import subprocess
                    subprocess.run(['git', 'commit', '-m', commit_message])
                    console.print("[green]Commit created successfully![/green]")
                    console.print("[bold]Tip: Now, You can push it with 'git push' 🫡[/bold]")
                
    except GitWiseError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    except InvalidGitRepositoryError as e:
        console.print(f"[red]Error: Not a git repository. Please run this command inside a git repository.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(Text(f"An unexpected error occurred: {str(e)}", style="red", justify="left"))
        traceback.print_exc()
        sys.exit(1)

def display_commit_message(message: str, token: int, is_interactive: bool = False):
    """Display generated commit message with formatting"""
    message = message.strip('`').strip()
    
    title = f"Generated Commit Message ({token} tokens)"
    cost = f"Cost: ${token * 0.150 / 1000000:.6f} USD 🥹 (gpt-4o-mini) (by https://openai.com/api/pricing/ date: 2024-10-20))"
    
    console.print(Panel.fit(
        Syntax(message, "markdown", theme="monokai", word_wrap=True),
        title=title,
        subtitle=cost,
        border_style="blue"
    ))
    
    escaped_message = (
        message.replace('"', '\\"')
              .replace('$', '\\$')
              .replace('\n', ' ')
              .replace("'", "\\'")
    )
    
    copyable_command = f'git commit -m "{escaped_message}"'
    
    console.print("[yellow]Tip: The main cost of tokens comes from the number of changes you made. We may optimize it in the future.🙏🙏[/yellow]")
    console.print("\n[blue]Execute this command to commit:[/blue]")
    
    console.print(Syntax(
        copyable_command,
        "bash",
        theme="monokai",
        word_wrap=True,
        padding=1
    ))
    
    try:
        pyperclip.copy(copyable_command)
        console.print("[green](Command copied to clipboard!)[/green]")
    except Exception:
        console.print("[yellow](Auto-copy not available)[/yellow]")
    
    if is_interactive:
        console.print("\n[dim]💡 Tip: Next time use 'git-wise start -i' for interactive commit![/dim]")

@cli.command()
def doctor():
    """Check Git-Wise configuration and environment"""
    console.print("[bold]Performing Git-Wise diagnostics...[/bold]\n")
    
    checks = []
    
    try:
        config = load_config()
        checks.append(("Configuration file", "✅ Found"))
        
        required_keys = ['default_language', 'openai_api_key', 'default_model', 'interactive', 'unlimited_chunk']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            checks.append(("Configuration content", f"⚠️ Missing: {', '.join(missing_keys)}"))
        else:
            checks.append(("Configuration content", "✅ Complete"))
    except Exception:
        checks.append(("Configuration file", "❌ Not found or invalid"))
    
    try:
        get_current_repo_info()
        checks.append(("Git repository", "✅ Valid"))
    except Exception:
        checks.append(("Git repository", "❌ Not found or invalid"))
    
    try:
        api_key = get_api_key(False)
        if api_key:
            checks.append(("API key", "✅ Found"))
        else:
            checks.append(("API key", "❌ Missing"))
    except Exception:
        checks.append(("API key", "❌ Error checking"))
    
    for check, status in checks:
        console.print(f"{check}: {status}")
        
@cli.command()
def show_config():
    """Show current configuration"""
    config = load_config()
    
    display_config = {}
    for key, value in config.items():
        if key == 'openai_api_key':
            display_config[key] = f"{value[:6]}...{value[-4:]}" if value else "Not set"
        elif key == 'default_language':
            language = next((lang for lang in Language if lang.value[1] == value), None)
            display_config[key] = language.value[0] if language else value
        elif key == 'detail_level':
            detail = next((level for level in DetailLevel if level.value[1] == value), None)
            display_config[key] = detail.value[0] if detail else value
        elif key == 'default_model':
            model = next((m for m in Model if m.value[1] == value), None)
            display_config[key] = model.value[0] if model else value
        elif key == 'interactive':
            display_config[key] = "Enabled" if value else "Disabled"
        elif key == 'unlimited_chunk':
            display_config[key] = "Enabled" if value else "Disabled"
        else:
            display_config[key] = value

    for key, value in display_config.items():
        console.print(f"[bold green]{key}:[/bold green] {value}")

@cli.command()
def show_diff():
    """Show staged changes"""
    try:
        diffs_for_user = get_all_staged_diffs(for_prompt=False)
        if not diffs_for_user:
            console.print("[yellow]No staged changes found.[/yellow]")
            return
        print_staged_changes(diffs_for_user)
        
    except Exception as e:
        console.print(f"[bold red]Error: {str(e).replace('[', '').replace(']', '')}[/bold red]")
        sys.exit(1)
        
@cli.command()
@click.option('--default-language', '-l', is_flag=True, help='Set default language')
@click.option('--detail-level', '-d', is_flag=True, help='Set detail level')
@click.option('--api-key', '-k', is_flag=True, help='Set OpenAI API key')
@click.option('--model', '-m', is_flag=True, help='Set default model')
@click.option('--interactive', '-i', is_flag=True, help='Set interactive mode')
@click.option('--unlimited-chunk', '-u', is_flag=True, help='Set unlimited chunk mode')
def config(default_language, detail_level, api_key, model, interactive, unlimited_chunk):
    """Update specific configuration settings"""
    config = load_config()
    
    if default_language:
        config = configure_language(config)
    
    if detail_level:
        config = configure_detail_level(config)
    
    if api_key:
        config = configure_api_key(config)
    
    if model:
        config = configure_model(config)
    
    if interactive:
        config = configure_interactive(config)
    
    if unlimited_chunk:
        config = configure_unlimited_chunk(config)
    
    if not any([default_language, detail_level, api_key, model, interactive, unlimited_chunk]):
        console.print("[yellow]No configuration changes specified. Use options to update specific settings.[/yellow]")
        console.print("Available options:")
        console.print("  --default-language, -l  Set default language")
        console.print("  --detail-level, -d      Set detail level")
        console.print("  --api-key, -k           Set OpenAI API key")
        console.print("  --model, -m             Set default model")
        console.print("  --interactive, -i       Set interactive mode")
        console.print("  --unlimited-chunk, -u   Set unlimited chunk mode")
        return
    
    save_config(config)
    console.print("[green]Configuration updated successfully![/green]")

def print_welcome_screen():
    welcome_message = """
    [bold green]
     ____  _  _    __        ___          
    / ___|(_)| |_  \ \      / (_) ___  ___ 
   | |  _ | || __|  \ \ /\ / /| |/ __|/ _ \\
   | |_| || || |_    \ V  V / | |\__ \  __/
    \____|_| \__|     \_/\_/  |_||___/\___|
    [/bold green]
    
    [bold]Git-Wise v{VERSION}[/bold]
    Your intelligent Git commit message generator.
    
    [blue]Available commands:[/blue]
    • git-wise init       - Configure Git-Wise
    • git-wise start      - Generate commit messages
    • git-wise doctor     - Check system status
    • git-wise show-diff  - Show staged changes
    • git-wise config     - Update specific settings
    
    Use 'git-wise --help' for more information.
    
    [italic]Visit https://github.com/varhuman/git-wise for documentation[/italic]
    """
    console.print(Panel(welcome_message, border_style="green"))

def main():
    cli()

if __name__ == '__main__':
    main()
