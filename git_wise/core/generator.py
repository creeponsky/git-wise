from enum import Enum
from openai import OpenAI
from git_wise.config import get_api_key
from typing import Dict, Any

class AIProvider(Enum):
    OPENAI = "openai"
    # TODO: add more providers. like:
    # - github copilot
    # - claude
    # - ...?

class CommitMessageGenerator:
    def __init__(self, provider: AIProvider):
        self.provider = provider
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        if self.provider == AIProvider.OPENAI:
            api_key = get_api_key()
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError("Unsupported AI provider")

    def generate_commit_message(self, diff: Dict[str, str], language: str, detail_level: str, repo_info: Dict[str, Any]):
        system_prompt = f"""
        You are a Git commit message generator that follows conventional commit practices. Your task is to generate a clear, concise, and meaningful commit message based on the staged changes provided.
        Key guidelines for generating commit messages:

        Start with a type prefix (feat, fix, docs, style, refactor, test, chore)
        Keep the first line under 72 characters
        Use the imperative mood ("add" not "added" or "adds")
        Be descriptive but concise
        Focus on WHY and WHAT changed, not HOW

        Configuration:

        Detail level: {detail_level}

        detailed: Include comprehensive description in body
        brief: Single line with essential information
        minimal: Type and core change only

        Language preference: {language}
        Repository context: {repo_info}

        Please generate a commit message following these guidelines. If the changes affect multiple distinct areas, consider suggesting separate commits for better organization.
        The commit message should follow this format:
        <type>[optional scope]: <description>
        [optional body]
        [optional footer(s)]
        Example of good commit messages:

        feat(auth): add password reset functionality
        fix: resolve null pointer in user profile
        docs: update API documentation
        refactor(api): simplify error handling logic

        IMPORTANT: Your response must contain ONLY the commit message(s). Do not include any explanations, comments, or additional content. If suggesting multiple commits, separate them with a blank line.
        """

        user_prompt = f"Staged changes: {diff}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        max_tokens = {
            'detailed': 500,
            'brief': 200,
            'minimal': 100
        }

        if self.provider == AIProvider.OPENAI:
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=max_tokens[detail_level],
                n=1,
                temperature=0.7,
            )
            return completion.choices[0].message.content.strip()
        else:
            raise ValueError("Unsupported AI provider")
