import click
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
import questionary
from git_wise.core.analyzer import analyze_changes
from git_wise.core.generator import CommitMessageGenerator
from git_wise.core.splitter import split_commits
from git_wise.config import load_config, save_config, get_api_key
from git_wise.utils.git_utils import get_all_staged_diffs, get_current_repo_info, print_staged_changes
from git_wise.core.generator import AIProvider
import sys
from git_wise.utils.exceptions import GitWiseError
from git.exc import InvalidGitRepositoryError
from typing import List
import os
from pathlib import Path
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
def start(language, detail, use_author_key, interactive):
    """Generate commit messages for staged changes"""
    try:
        console.print("[bold]Checking configuration...[/bold]")
        config = load_config()
        api_key = get_api_key(use_author_key)
        if not api_key:
            raise GitWiseError(
                "OpenAI API key not set. Please run 'git-wise init' to configure, "
                "or use --use-author-key option."
            )
        
        generator = CommitMessageGenerator(AIProvider.OPENAI, model=config.get('default_model'))
        
        language = language or config.get('default_language', 'en')
        detail = detail or config.get('detail_level', 'brief')
        
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
                
        console.print("staged changes found.")
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
            display_commit_message(commit_message, token)
            
            if interactive:
                if questionary.confirm("Do you want to use this commit message?").ask():
                    import subprocess
                    subprocess.run(['git', 'commit', '-m', commit_message])
                    console.print("[green]Commit created successfully![/green]")
                
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
        
def display_commit_message(message: str, token: int):
    """Display generated commit message with formatting"""
    title = f"Generated Commit Message ({token} tokens, if you use gpt-4o-mini, it will cost ${token * 0.150 / 1000000} USD 😎🥹)"
    console.print(Panel.fit(
        message,
        title=title,
        border_style="blue"
    ))
    
    # 处理消息以适应命令行
    escaped_message = (
        message.replace('"', '\\"')  # 转义双引号
              .replace('$', '\\$')   # 转义美元符号
              .replace('\n', '\\n')  # 将换行符转换为字面量
              .replace("'", "\\'")   # 转义单引号
    )
    
    # 创建可复制的命令
    copyable_command = f"git commit -m '{escaped_message}'"
    
    console.print("\n[blue]Copy and paste this command to commit:[/blue]")
    
    # 使用 Panel 来突出显示命令
    command_panel = Panel(
        Text(copyable_command, style="green"),
        title="Command to Copy",
        border_style="green"
    )
    console.print(command_panel)
    
    # 添加一个简化版本的提示
    console.print("[dim]Or next time, you can use 'git-wise start -i' to let me commit! [/dim]")

# def display_commit_message(message: str, token: int):
#     """Display generated commit message with formatting"""
#     title = f"Generated Commit Message ({token} tokens,if you use gpt-4o-mini, it will cost ${token * 0.150 / 1000000} USD 😎🥹)"
#     console.print(Panel.fit(
#         message,
#         title=title,
#         border_style="blue"
#     ))
    
#     # 创建一个可以直接复制粘贴的版本
#     escaped_message = message.replace('"', '\\"').replace('$', '\\$')
#     copyable_command = f'git commit -m "{escaped_message}"'
    
#     console.print("\n[blue]You can commit using:[/blue]")
#     console.print(Text(f"{copyable_command}", style="green", justify="left"))
    
#     console.print("\n[yellow]Copy the above command to commit, or use this for manual editing:[/yellow]")
#     console.print(Text(f"git commit -m \"{message.split()[0]}...\"", style="green", justify="left"))

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
        
# View current configuration
@cli.command()
def show_config():
    """Show current configuration"""
    config = load_config()
    
    # Process and display configuration information
    display_config = {}
    for key, value in config.items():
        if key == 'openai_api_key':
            # Only show the first 6 and last 4 characters of the API key
            display_config[key] = f"{value[:6]}...{value[-4:]}" if value else "Not set"
        elif key == 'default_language':
            # Display the full name of the language
            language = next((lang for lang in Language if lang.value[1] == value), None)
            display_config[key] = language.value[0] if language else value
        elif key == 'detail_level':
            # Display the description of the detail level
            detail = next((level for level in DetailLevel if level.value[1] == value), None)
            display_config[key] = detail.value[0] if detail else value
        elif key == 'default_model':
            # Display the full name of the model
            model = next((m for m in Model if m.value[1] == value), None)
            display_config[key] = model.value[0] if model else value
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
def config(default_language, detail_level, api_key, model):
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
    
    if not any([default_language, detail_level, api_key, model]):
        console.print("[yellow]No configuration changes specified. Use options to update specific settings.[/yellow]")
        console.print("Available options:")
        console.print("  --default-language, -l  Set default language")
        console.print("  --detail-level, -d      Set detail level")
        console.print("  --api-key, -k           Set OpenAI API key")
        console.print("  --model, -m             Set default model")
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
