import click
from rich import print
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
import questionary
from git_wise.core.analyzer import analyze_changes
from git_wise.core.generator import CommitMessageGenerator
from git_wise.core.splitter import split_commits
from git_wise.config import load_config, save_config, get_api_key
from git_wise.utils.git_utils import get_all_staged_diffs, get_current_repo_info
from git_wise.core.generator import AIProvider
import sys
from git_wise.utils.exceptions import GitWiseError
from git.exc import InvalidGitRepositoryError
from enum import Enum
import os
from pathlib import Path

console = Console()
VERSION = "0.1.0"

class Language(Enum):
    ENGLISH = ("English (default)", "en")
    CHINESE = ("Chinese", "zh")
    CUSTOM = ("Custom", None)

class DetailLevel(Enum):
    DETAILED = ("Detailed - Comprehensive commit messages with context", "detailed")
    BRIEF = ("Brief - Concise but informative messages (Recommended)", "brief")
    MINIMAL = ("Minimal - Just the essential changes", "minimal")

class Model(Enum):
    GPT4O_MINI = ("GPT-4o-mini (Recommended, sufficient for most cases and more cost-effective)", "gpt-4o-mini")
    GPT4O = ("GPT-4o (Full capability, higher cost)", "gpt-4o")

@click.group()
@click.version_option(VERSION, '-v', '--version', message='Git-Wise Version: %(version)s')
@click.help_option('-h', '--help')
def cli():
    """
    Git-Wise: An intelligent Git commit message generator.
    
    Use 'git-wise COMMAND --help' for more information about specific commands.
    """
    pass

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
        
    detail_level = questionary.select(
        "Select the detail level for commit messages:",
        choices=[level.value[0] for level in DetailLevel],
        default=DetailLevel.BRIEF.value[0]
    ).ask()
    selected_detail = next(level for level in DetailLevel if level.value[0] == detail_level)

    # api_key = questionary.text(
    #     "Enter your OpenAI API key (may be used for other AI providers in the future):",
    #     validate=lambda text: len(text) > 0
    # ).ask()
    api_key = input("Enter your OpenAI API key (may be used for other AI providers in the future):").strip()
    while not api_key:
        print("API key cannot be empty, please re-enter.")
        api_key = input("Enter your OpenAI API key (may be used for other AI providers in the future):").strip()
    
    model_choice = questionary.select(
        "Select the default model:",
        choices=[model.value[0] for model in Model],
        default=Model.GPT4O_MINI.value[0]
    ).ask()
    selected_model = next(model for model in Model if model.value[0] == model_choice)

    config.update({
        'default_language': default_language,
        'openai_api_key': api_key,
        'default_model': selected_model.value[1],
        'detail_level': selected_detail.value[1]
    })
    
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
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode')
def start(language, detail, use_author_key, interactive):
    """Generate commit messages for staged changes"""
    try:
        config = load_config()
        api_key = get_api_key(use_author_key)
        if not api_key:
            raise GitWiseError(
                "OpenAI API key not set. Please run 'git-wise init' to configure, "
                "or use --use-author-key option."
            )
        
        generator = CommitMessageGenerator(AIProvider.OPENAI)
        
        language = language or config.get('default_language', 'en')
        detail = detail or config.get('detail_level', 'brief')
        
        diffs = get_all_staged_diffs()
        repo_info = get_current_repo_info()
        
        if not diffs:
            raise GitWiseError("No staged files found. Stage your changes using 'git add' first.")
        
        changes = analyze_changes(diffs)
        
        # if split:
        if False:
            commits = split_commits(changes)
            for i, commit_changes in enumerate(commits, 1):
                commit_message = generator.generate_commit_message(
                    commit_changes, language, detail, repo_info
                )
                display_commit_message(commit_message, i if len(commits) > 1 else None)
                
                if interactive:
                    if not questionary.confirm("Do you want to use this commit message?").ask():
                        continue
                    
                    # Execute git commit
                    import subprocess
                    subprocess.run(['git', 'commit', '-m', commit_message])
                    console.print("[green]Commit created successfully![/green]")
        else:
            commit_message = generator.generate_commit_message(changes, language, detail, repo_info)
            display_commit_message(commit_message)
            
            if interactive:
                if questionary.confirm("Do you want to use this commit message?").ask():
                    import subprocess
                    subprocess.run(['git', 'commit', '-m', commit_message])
                    console.print("[green]Commit created successfully![/green]")
                
    except GitWiseError as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        sys.exit(1)
    except InvalidGitRepositoryError as e:
        console.print(f"[bold red]Error: Not a git repository. Please run this command inside a git repository.[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {str(e)}[/bold red]")
        sys.exit(1)

def display_commit_message(message, commit_num=None):
    """Display generated commit message with formatting"""
    title = "Generated Commit Message"
    if commit_num is not None:
        title += f" ({commit_num})"
        
    console.print(Panel.fit(
        message,
        title=title,
        border_style="blue"
    ))
    
    console.print("\n[blue]You can commit using:[/blue]")
    console.print(f"git commit -m \"{message}\"")
    print()

@cli.command()
def doctor():
    """Check Git-Wise configuration and environment"""
    console.print("[bold]Performing Git-Wise diagnostics...[/bold]\n")
    
    checks = []
    
    # Check configuration file
    try:
        config = load_config()
        checks.append(("Configuration file", "✅ Found"))
        
        # Check necessary configuration items
        required_keys = ['default_language', 'openai_api_key', 'default_model']
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            checks.append(("Configuration content", f"⚠️ Missing: {', '.join(missing_keys)}"))
        else:
            checks.append(("Configuration content", "✅ Complete"))
    except Exception:
        checks.append(("Configuration file", "❌ Not found or invalid"))
    
    # Check Git repository
    try:
        get_current_repo_info()
        checks.append(("Git repository", "✅ Valid"))
    except Exception:
        checks.append(("Git repository", "❌ Not found or invalid"))
    
    # Check API key
    try:
        api_key = get_api_key(False)
        if api_key:
            checks.append(("API key", "✅ Found"))
        else:
            checks.append(("API key", "❌ Missing"))
    except Exception:
        checks.append(("API key", "❌ Error checking"))
    
    # Display check results
    for check, status in checks:
        console.print(f"{check}: {status}")

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
    • git-wise init   - Configure Git-Wise
    • git-wise start  - Generate commit messages
    • git-wise doctor - Check system status
    
    Use 'git-wise --help' for more information.
    
    [italic]Visit https://github.com/varhuman/git-wise for documentation[/italic]
    """
    console.print(Panel(welcome_message, border_style="green"))

def main():
    cli()

if __name__ == '__main__':
    main()
