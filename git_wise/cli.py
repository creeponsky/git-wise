import click
from rich import print
from git_wise.core.analyzer import analyze_changes
from git_wise.core.generator import CommitMessageGenerator
from git_wise.core.splitter import split_commits
from git_wise.config import load_config, save_config, get_api_key
from git_wise.utils.git_utils import get_all_staged_diffs, get_current_repo_info
from git_wise.core.generator import AIProvider
import sys
from git_wise.utils.exceptions import GitWiseError
from git.exc import InvalidGitRepositoryError
@click.group()
def cli():
    pass

@cli.command()
def init():
    """Initialize or reconfigure Git-Wise"""
    config = load_config()
    
    if config:
        if click.confirm("Git-Wise is already configured. Do you want to clear the settings and reconfigure?", default=False):
            config = {}
        else:
            print("[green]Keeping existing configuration.[/green]")
            return

    languages = {
        '1': 'en',
        '2': 'zh',
        '3': 'other'
    }
    
    choice = click.prompt(
        "Select your default commit message language:\n1. English\n2. Chinese\n3. Other",
        type=click.Choice(['1', '2', '3']),
        default='1'
    )
    
    if choice == '3':
        default_language = click.prompt("Enter the language code (e.g., fr, de, es. you can also use the language name)")
    else:
        default_language = languages[choice]
        
    # 让他选择Detail level: [detailed|brief|minimal]
    detail_level = click.prompt("Select the detail level:\n1. detailed\n2. brief\n3. minimal", type=click.Choice(['1', '2', '3']), default='2')
    detail_level = 'detailed' if detail_level == '1' else 'brief' if detail_level == '2' else 'minimal'

    api_key = click.prompt("Enter your OpenAI API key(If I can pay my openai bill, I will add new option for you! T T)", hide_input=True)
    
    model_choice = click.prompt(
        "Select the default model:\n1. gpt-4o-mini (recommended, it's enough for most case and cheaper)\n2. gpt-4o",
        type=click.Choice(['1', '2']),
        default='1'
    )
    default_model = 'gpt-4o-mini' if model_choice == '1' else 'gpt-4o'

    config['default_language'] = default_language
    config['openai_api_key'] = api_key
    config['default_model'] = default_model
    config['detail_level'] = detail_level
    save_config(config)
    
    print("[green]Configuration saved successfully![/green]")
    print_welcome_screen()
    
@cli.command()
@click.option('--language', '-lan', default=None, help='Language option (default: language in config)')
@click.option('--detail', '-d', type=click.Choice(['detailed', 'brief', 'minimal']), default='medium', help='Commit message detail (default: medium)')
@click.option('--split', '-s', is_flag=True, help='Split commits')
@click.option('--use-author-key', '-a', is_flag=True, help='Use author\'s API key')
def start(language, detail, split, use_author_key):
    """Automatically generate Git commit messages"""
    try:
        config = load_config()
        api_key = get_api_key(use_author_key)
        if not api_key:
            raise GitWiseError("OpenAI API key not set. Please run 'git-wise init' to configure, or use --use-author-key option.")
        
        generator = CommitMessageGenerator(AIProvider.OPENAI)
        
        language = language or config.get('default_language', 'en')
        detail = detail or config.get('detail_level', 'brief')
        
        diffs = get_all_staged_diffs()
        repo_info = get_current_repo_info()
        
        if not diffs:
            raise GitWiseError("No staged files.")
        
        changes = analyze_changes(diffs)
        
        if split:
            commits = split_commits(changes)
            for i, commit_changes in enumerate(commits, 1):
                commit_message = generator.generate_commit_message(commit_changes, language, detail, repo_info)
                print(f"[green]Generated commit {i} message:[/green]\n\n{commit_message}\n")
                print("[blue]You can commit using:[/blue]")
                print(f"git commit -m \"{commit_message}\"")
                print()
        else:
            commit_message = generator.generate_commit_message(changes, language, detail)
            print(f"[green]Generated commit message:[/green]\n\n{commit_message}\n")
            print("[blue]You can commit using:[/blue]")
            print(f"git commit -m \"{commit_message}\"")
    except GitWiseError as e:
        print(f"[bold red]Error: {str(e)}[/bold red]")
        sys.exit(1)
        # InvalidGitRepositoryError
    except InvalidGitRepositoryError as e:
        print(f"[bold red]Error: {str(e)}[/bold red]")
        sys.exit(1)
    except Exception as e:
        print(f"[bold red]An unknown error occurred: {str(e)}[/bold red]")
        sys.exit(1)

def print_welcome_screen():
    welcome_message = """
    [bold green]
     ____  _  _    __        ___          
    / ___|(_)| |_  \ \      / (_) ___  ___ 
   | |  _ | || __|  \ \ /\ / /| |/ __|/ _ \\
   | |_| || || |_    \ V  V / | |\__ \  __/
    \____|_| \__|     \_/\_/  |_||___/\___|
    [/bold green]
    
    Welcome to Git-Wise!(Pre-alpha version)
    Your intelligent Git commit message generator.
    
    Type 'git-wise --help' for available commands.
    
    if you want to know more about this project, you can visit https://github.com/varhuman/git-wise
    """
    print(welcome_message)

def main():
    cli()

if __name__ == '__main__':
    main()
