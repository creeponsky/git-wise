from git import Repo
from git.exc import GitCommandError

def analyze_changes(staged_files):
    repo = Repo('.')
    changes = []
    for file_path in staged_files:
        try:
            # 使用 -- 来明确指定文件路径
            diff = repo.git.diff('--cached', '--', file_path)
            changes.append({
                'path': file_path,
                'change_type': 'modified',  # 简化处理，实际上可能需要更复杂的逻辑
                'lines_added': diff.count('\n+'),
                'lines_removed': diff.count('\n-'),
                'diff': diff
            })
        except GitCommandError as e:
            print(f"无法获取文件 {file_path} 的差异信息: {str(e)}")
            continue
    return changes
