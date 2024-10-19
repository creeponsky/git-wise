import os
from git import Repo, InvalidGitRepositoryError
from git.repo import Repo as GitRepo
import git
from github import Github
from typing import List, Dict, Optional, Tuple
import requests
from urllib.parse import urlparse
import time

def get_repo(path = os.getcwd()) -> GitRepo:
    try:
        return Repo(path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        raise InvalidGitRepositoryError(f"not a git repo: {path}")

def get_current_repo_name() -> Optional[str]:
    try:
        repo = get_repo()
        
        try:
            if not repo.remotes:
                return os.path.basename(repo.working_dir)
                
            remote_url = repo.remotes.origin.url
            if remote_url.endswith('.git'):
                remote_url = remote_url[:-4]
            repo_name = remote_url.split('/')[-2] + '/' + remote_url.split('/')[-1]
            return repo_name
        except (AttributeError, IndexError):
            print(f"Warning: Failed to get current repo name for {repo.working_dir}")
            return os.path.basename(repo.working_dir)
            
    except git.exc.InvalidGitRepositoryError:
        print(f"Warning: Failed to get current repo name for {os.getcwd()}")
        return None
    except Exception as e:
        print(f"Warning: {str(e)}")
        return None

def get_staged_files(repo: GitRepo=get_repo()) -> List[str]:
    try:
        return [item.a_path for item in repo.index.diff('HEAD')]
    except git.exc.GitCommandError:
        # Handle case for initial commit when HEAD doesn't exist
        print(f"Warning: Failed to get staged files for {repo.working_dir}")
        return [item.a_path for item in repo.index.diff(None)]

def get_file_diff(file_path: str, repo: GitRepo=get_repo()) -> str:
    try:
        diff: str = repo.git.diff('--cached', file_path)
        lines: List[str] = diff.split('\n')
        modified_lines: List[str] = [line for line in lines if line.startswith('+') or line.startswith('-')]
        return '\n'.join(modified_lines)
    except git.exc.GitCommandError:
        print(f"Warning: Failed to get diff for {file_path}")
        return ""

def get_all_staged_diffs(repo: GitRepo=get_repo()) -> Dict[str, Dict[str, str]]:
    diffs = {}
    try:
        staged_files = repo.index.diff("HEAD")
    except git.exc.GitCommandError:
        # Handle case for initial commit when HEAD doesn't exist
        staged_files = repo.index.diff(None)

    for item in staged_files:
        try:
            if item.change_type == 'A':  # New file
                try:
                    content = repo.git.show(f':0:{item.b_path}')
                except git.exc.GitCommandError:
                    content = "Unable to retrieve file content"
                diffs[item.b_path] = {
                    'type': 'new',
                    'content': content
                }
            elif item.change_type == 'D':  # Deleted file
                diffs[item.a_path] = {
                    'type': 'deleted',
                    'content': ''
                }
            elif item.change_type == 'M':  # Modified file
                try:
                    content = repo.git.diff('HEAD', '--', item.b_path)
                except git.exc.GitCommandError:
                    content = "Unable to retrieve file diff"
                diffs[item.b_path] = {
                    'type': 'modified',
                    'content': content
                }
            elif item.change_type == 'R':  # Renamed file
                try:
                    content = repo.git.diff('HEAD', '--', item.b_path)
                except git.exc.GitCommandError:
                    content = "Unable to retrieve file diff"
                diffs[item.b_path] = {
                    'type': 'renamed',
                    'old_path': item.a_path,
                    'content': content
                }
        except Exception as e:
            print(f"Warning: Error processing file {item.a_path or item.b_path}: {str(e)}")

    # Handle untracked new files
    try:
        untracked = repo.untracked_files
        for file in untracked:
            if file in repo.index.entries:
                file_path = os.path.join(repo.working_tree_dir, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    content = "Binary file"
                except Exception as e:
                    content = f"Unable to read file content: {str(e)}"
                diffs[file] = {
                    'type': 'new',
                    'content': content
                }
    except Exception as e:
        print(f"Warning: Error processing untracked files: {str(e)}")

    return diffs

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

# def detect_main_language(repo_path: str) -> Optional[str]:
#     language_extensions = {
#         '.py': 'Python',
#         '.js': 'JavaScript',
#         '.java': 'Java',
#         '.cpp': 'C++',
#         '.go': 'Go',
#     }
    
#     try:
#         file_counts = {}
#         for root, _, files in os.walk(repo_path):
#             if '.git' in root:  # Skip .git directory
#                 continue
#             for file in files:
#                 _, ext = os.path.splitext(file)
#                 if ext in language_extensions:
#                     lang = language_extensions[ext]
#                     file_counts[lang] = file_counts.get(lang, 0) + 1
        
#         return max(file_counts, key=file_counts.get) if file_counts else None
#     except Exception:
#         print(f"Warning: Failed to detect main language for {repo_path}")
#         return None

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
print(get_all_staged_diffs())

# Test function
def test_get_all_staged_diffs():
    try:
        result = get_all_staged_diffs()
        print("Staged file differences:")
        for file, diff in result.items():
            print(f"File: {file}")
            print(f"Type: {diff['type']}")
            print(f"Content: {diff['content'][:100]}...")  # Print only the first 100 characters
            print("---")
    except Exception as e:
        print(f"Error getting staged file differences: {str(e)}")
        print("If this error persists, please report it to the developer at https://github.com/varhuman/git-wise/issues")

# Run test
test_get_all_staged_diffs()
