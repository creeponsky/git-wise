from git import Repo

def analyze_changes(staged_files):
    repo = Repo('.')
    changes = []
    for file_path in staged_files:
        diff = repo.git.diff('--cached', file_path)
        changes.append({
            'path': file_path,
            'change_type': 'modified',  # 简化处理，实际上可能需要更复杂的逻辑
            'lines_added': diff.count('\n+'),
            'lines_removed': diff.count('\n-'),
            'diff': diff
        })
    return changes
