import os
from git.repo import Repo as GitRepo
import git
from typing import List, Dict, Optional, Union
import requests
from urllib.parse import urlparse
import traceback
from git import GitCommandError, InvalidGitRepositoryError
from rich.console import Console

console = Console()

def get_repo(path=os.getcwd()) -> GitRepo:
    try:
        return GitRepo(path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        raise InvalidGitRepositoryError(f"Not a git repository: {path}\n git-wise requires a git repository to work. you need go to a git repository first.🥹")

def get_all_staged_diffs(repo: GitRepo = get_repo(), for_prompt: bool = True) -> Dict[str, Union[Dict, List[str]]]:
    """
    Get all staged differences in the repository with two output modes.
    
    Args:
        repo: Git repository object
        for_prompt: If True, use concise AI prompting format; if False, use detailed user format
    
    Returns:
        Dictionary with file changes information, format varies by mode:
        
        AI mode format (concise):
        {
            "file_path": {
                "type": "new|modified|deleted|renamed",
                "changes": "only_changed_portions",
                "size": file_size_in_bytes,  # Only for new files
                "truncated": boolean  # True if content was truncated
            }
        }
        
        User mode format (detailed):
        {
            "file_path": {
                "type": "new|modified|deleted|renamed",
                "content": "full_content_or_diff",
                "old_path": "original_path_if_renamed",
                "error": "error_message_if_any"
            }
        }
    """

    diffs = {}
    staged_files = set()
    
    try:
        # Handle detached HEAD state
        try:
            current_commit = repo.head.commit
        except TypeError:
            current_commit = None

        # Get staged changes
        if current_commit:
            staged = repo.index.diff(current_commit)
        else:
            staged = repo.index.diff(None)
        staged_files.update([(item.a_path, item.b_path) for item in staged])
        # Process each file
        for a_path, b_path in staged_files:
            current_path = b_path or a_path
            if current_path is None:
                # Log the occurrence of a None path for debugging
                print(f"Warning: Encountered None path. a_path: {a_path}, b_path: {b_path}")
                continue

            try:
                status = get_file_status(a_path, b_path)
                if status is None:
                    # Log unexpected status for debugging
                    print(f"Warning: Unexpected file status for {current_path}. a_path: {a_path}, b_path: {b_path}")
                    continue

                if status not in ["new", "modified", "deleted", "renamed"]:
                    # Handle unexpected status
                    print(f"Warning: Unhandled file status '{status}' for {current_path}")
                    status = "unknown"

                if for_prompt:
                    file_info = process_file_ai_mode(repo, current_path, status, a_path)
                else:
                    file_info = process_file_user_mode(repo, current_path, status, a_path)

                diffs[current_path] = file_info

            except Exception as e:
                error_info = {
                    "type": "error",
                    "error": str(e)
                }
                if for_prompt:
                    error_info["changes"] = ""
                else:
                    error_info["content"] = ""
                diffs[current_path] = error_info
                if not for_prompt:
                    console.print(f"[yellow]Warning: Error processing {current_path}: {str(e)}[/yellow]")

    except Exception as e:
        if not for_prompt:
            console.print(f"[red]Error accessing repository: {str(e)}[/red]")
        return {}

    return diffs

def process_file_ai_mode(repo: GitRepo, current_path: str, status: str, a_path: Optional[str]) -> List[str]:
    MAX_CONTENT_SIZE = 50000  # 50KB limit for AI processing

    file_info = {
        "type": status,
        "content": ""
    }

    try:
        if status == "new":
            content = get_new_file_content(repo, current_path)
            size = len(content.encode('utf-8'))
            if size <= MAX_CONTENT_SIZE:
                file_info["content"] = content
            else:
                file_info["content"] = f"[Large new file: {size/1024:.1f}KB]"
        
        elif status == "modified":
            diff = get_modified_file_diff(repo, current_path)
            file_info["content"] = extract_diff_hunks(diff)
        
        elif status == "renamed":
            file_info["old_path"] = a_path
            file_info["content"] = extract_diff_hunks(get_modified_file_diff(repo, current_path))
        
        elif status == "deleted":
            file_info["content"] = "[File deleted]"

    except Exception as e:
        file_info["content"] = f"[Error: {str(e)}]"

    return [current_path, file_info["type"], file_info["content"]]

def process_file_user_mode(repo: GitRepo, current_path: str, status: str, a_path: Optional[str]) -> Dict:
    """Process file changes in user mode (detailed output)"""
    file_info = {
        "type": status,
        "content": "",
        "error": None
    }

    if status == "new":
        file_info["content"] = get_new_file_content(repo, current_path)
    elif status == "modified":
        file_info["content"] = get_modified_file_diff(repo, current_path)
    elif status == "deleted":
        file_info["content"] = get_deleted_file_content(repo, current_path)
    elif status == "renamed":
        file_info.update({
            "old_path": a_path,
            "content": get_modified_file_diff(repo, current_path)
        })

    return file_info

def extract_diff_hunks(diff_content: str) -> str:
    """Extract only the changed hunks from a diff output"""
    lines = diff_content.split('\n')
    hunks = []
    current_hunk = []
    
    for line in lines:
        if line.startswith('@@'):
            if current_hunk:
                hunks.append('\n'.join(current_hunk))
                current_hunk = []
        if line.startswith(('@@', '+', '-')) and not line.startswith('+++') and not line.startswith('---'):
            current_hunk.append(line)
    
    if current_hunk:
        hunks.append('\n'.join(current_hunk))
    
    return '\n'.join(hunks)

def get_file_status(a_path: Optional[str], b_path: Optional[str]) -> Optional[str]:
    """Determine the status of a file in the repository."""
    try:
        if a_path is None and b_path:
            return "new"
        elif a_path and b_path is None:
            return "deleted"
        elif a_path and b_path and a_path != b_path:
            return "renamed"
        elif a_path and b_path and a_path == b_path:
            return "modified"
        return None
    except Exception:
        return None

def get_new_file_content(repo: GitRepo, file_path: str) -> str:
    """Get content of a new file."""
    try:
        return repo.git.show(f':0:{file_path}')
    except GitCommandError:
        try:
            if isinstance(repo.working_dir, tuple):
                # If repo.working_dir is unexpectedly a 6tuple, use the first element
                working_dir = repo.working_dir[0] if repo.working_dir else ''
            else:
                working_dir = repo.working_dir

            full_path = os.path.join(working_dir, file_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            return "[Binary file]"
        except TypeError as e:
            return f"[Unable to read file content: {str(e)}]"
        except Exception as e:
            return f"[Unable to read file content: {str(e)}]"

def get_modified_file_diff(repo: GitRepo, file_path: str) -> str:
    """Get diff of a modified file."""
    try:
        return repo.git.diff('--cached', '--', file_path)
    except GitCommandError as e:
        return f"[Unable to get diff: {str(e)}]"

def get_deleted_file_content(repo: GitRepo, file_path: str) -> str:
    """Get content of a deleted file."""
    try:
        return repo.git.show(f'HEAD:{file_path}')
    except GitCommandError:
        return "[Content not available]"
    
def print_staged_changes(diffs: Dict[str, Union[Dict, List[str]]]) -> None:
    """Pretty print staged changes."""
    if not diffs:
        console.print("[yellow]No staged changes found.[/yellow]")
        return

    console.print("\n[bold blue]Staged Changes:[/bold blue]")
    for file_path, info in diffs.items():
        
        type_colors = {
            "new": "green",
            "modified": "yellow",
            "deleted": "red",
            "renamed": "blue",
            "error": "red"
        }
        if isinstance(info, list):
            color = type_colors.get(info[1], "white")
            
            console.print(f"\n[{color}]File: {file_path}[/{color}]")
            console.print(f"Type: {info[1]}")
            
            if info[1] == "renamed":
                console.print(f"Old path: {info[2]}")
            
            if info[1] == "error":
                console.print(f"[red]Error: {info[2]}[/red]")
            elif info[1] == "new":
                preview = info[2][:500] + ("..." if len(info[2]) > 500 else "")
                console.print("Content preview:")
                console.print(preview)
        else:
            color = type_colors.get(info["type"], "white")
        
            console.print(f"\n[{color}]File: {file_path}[/{color}]")
            console.print(f"Type: {info['type']}")
            
            if info["type"] == "renamed":
                console.print(f"Old path: {info.get('old_path', 'unknown')}")
            
            if info.get("error"):
                console.print(f"[red]Error: {info['error']}[/red]")
            elif content := info.get("content"):
                preview = content[:500] + ("..." if len(content) > 500 else "")
                console.print("Content preview:")
                console.print(preview)

def get_current_repo_info(repo_path='.') -> Optional[Dict]:
    try:
        repo = get_repo(repo_path)
        
        project_info = {
            'name': os.path.basename(repo.working_dir),
            'description': None,
            'language': None,
            # 'language': detect_main_language(), # I dont think it's necessary
            'default_branch': None
        }
        
        try:
            project_info['default_branch'] = repo.active_branch.name
        except (TypeError, AttributeError):
            print(f"Warning: Failed to get current branch for {repo.working_dir}")
            pass

        try:
            if repo.remotes:
                remote_url = repo.remotes.origin.url
                github_info = get_github_info(remote_url)
                if github_info:
                    project_info.update(github_info)
        except (AttributeError, git.exc.GitCommandError):
            print(f"Warning: Failed to get github info for {remote_url}")
            pass
        
        try:
            current_branch = repo.active_branch.name
        except (TypeError, AttributeError):
            current_branch = None
            print(f"Warning: Failed to get current branch for {repo.working_dir}")
        try:
            commits = list(repo.iter_commits(max_count=5))
            recent_commits = [{
                'message': commit.message,
                'author': commit.author.name,
                'date': commit.authored_datetime
            } for commit in commits]
        except (git.exc.GitCommandError, AttributeError):
            recent_commits = []
        
        try:
            branches = [branch.name for branch in repo.branches]
        except (git.exc.GitCommandError, AttributeError):
            branches = []
        
        return {
            'project_info': project_info,
            'current_branch': current_branch,
            'recent_commits': recent_commits,
            'branches': branches
        }
    except InvalidGitRepositoryError:
        return None
    except Exception as e:
        print(f"Warning: {str(e)}")
        return None

def get_github_info(remote_url: str) -> Optional[Dict]:
    parsed_url = urlparse(remote_url)
    if 'github.com' not in parsed_url.netloc:
        return None

    try:
        path_parts = parsed_url.path.strip('/').split('/')
        if len(path_parts) < 2:
            return None
        owner, repo = path_parts[:2]
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        response = requests.get(api_url, timeout=3)  # Short timeout
        if response.status_code == 200:
            data = response.json()
            return {
                'description': data.get('description'),
                'language': data.get('language'),
                'stars': data.get('stargazers_count'),
                'forks': data.get('forks_count')
            }
    except (requests.RequestException, ValueError, AttributeError):
        print(f"Warning: Failed to fetch GitHub info for {remote_url}")
        pass
    
    return None

# TODO: feature: get developer's old project, and learn from it
# def get_github_info_from_github_api(repo_name, access_token="nothing"):
#     g = Github(access_token)
#     repo = g.get_repo(repo_name)
    
#     # Get project information
#     project_info = {
#         'name': repo.name,
#         'description': repo.description,
#         'language': repo.language,
#         'default_branch': repo.default_branch
#     }
    
#     # Get commit convention (if there's a related file in .github directory)
#     try:
#         commit_convention = repo.get_contents('.github/COMMIT_CONVENTION.md')
#         project_info['commit_convention'] = commit_convention.decoded_content.decode()
#     except:
#         project_info['commit_convention'] = None
    
#     # Get recent commits
#     commits = repo.get_commits()[:5]
#     recent_commits = [{
#         'message': commit.commit.message,
#         'author': commit.commit.author.name,
#         'date': commit.commit.author.date
#     } for commit in commits]
    
#     # Get open issues
#     try:
#         open_issues = [{
#             'number': issue.number,
#             'title': issue.title
#         } for issue in list(repo.get_issues(state='open'))[:5]]
#     except IndexError:
#         open_issues = []  # Return an empty list if there are no open issues
    
#     return {
#         'project_info': project_info,
#         'recent_commits': recent_commits,
#         'open_issues': open_issues
#     }
# print(get_all_staged_diffs())


# Test function
def test_get_all_staged_diffs():
    """Test function for staged diffs."""
    try:
        diffs = get_all_staged_diffs()
        print(diffs)
        # print_staged_changes(diffs)
        
        # diffs_for_user = get_all_staged_diffs(for_prompt=False)
        # print_staged_changes(diffs_for_user)
    except InvalidGitRepositoryError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
    except Exception as e:
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        console.print(f"traceback: {traceback.format_exc()}")
        console.print("[yellow]If this error persists, please report it at https://github.com/varhuman/git-wise/issues[/yellow]")

# Run test
# test_get_all_staged_diffs()