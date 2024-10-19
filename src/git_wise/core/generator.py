from enum import Enum
from openai import OpenAI
from git_wise.config import get_api_key
from typing import Dict, Any, List, Union
import tiktoken
from rich.console import Console

console = Console()

class AIProvider(Enum):
    OPENAI = "openai"
    # TODO: add more providers. like:
    # - github copilot
    # - claude
    # - ...?
class TokenCounter:
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.encoding = tiktoken.encoding_for_model(model)
    
    def count_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens for a list of messages."""
        num_tokens = 0
        for message in messages:
            num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
            for key, value in message.items():
                num_tokens += len(self.encoding.encode(value))
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens -= 1  # role is always required and always 1 token
        num_tokens += 2  # every reply is primed with <im_start>assistant
        return num_tokens
    
class CommitMessageGenerator:
    MAX_CHUNKS = 3
    MAX_TOKENS = 16000  # Setting slightly below actual limit for safety
    
    def __init__(self, provider: AIProvider, model: str = "gpt-3.5-turbo"):
        self.provider = provider
        self.model = model
        self.client = None
        self.token_counter = TokenCounter(model)
        self._initialize_client()

    def _initialize_client(self):
        if self.provider == AIProvider.OPENAI:
            api_key = get_api_key()
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError("Unsupported AI provider")

    def _split_diff(self, diff: Union[Dict[str, str], List[Dict[str, str]]], num_chunks: int) -> List[Union[Dict[str, str], List[Dict[str, str]]]]:
        """Split the diff into roughly equal chunks."""
        if isinstance(diff, dict):
            items = list(diff.items())
        elif isinstance(diff, list):
            items = diff
        else:
            raise ValueError("Unsupported diff type")
        
        chunk_size = len(items) // num_chunks
        chunks = []
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            if isinstance(diff, dict):
                chunk_dict = dict(chunk)
                chunks.append(chunk_dict)
            else:
                chunks.append(chunk)
        
        return chunks

    def _create_messages(self, system_prompt: str, diff: Union[Dict[str, str], List[Dict[str, str]]]) -> List[Dict[str, str]]:
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Staged changes: {diff}"}
        ]

    def generate_commit_message(self, diff: Union[Dict[str, str], List[Dict[str, str]]], language: str, detail_level: str, repo_info: Dict[str, Any]) -> str:
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
        Language preference: {language}
        Repository context: {repo_info}

        IMPORTANT: Your response must contain ONLY the commit message(s). Do not include any explanations or comments.
        """

        messages = self._create_messages(system_prompt, diff)
        total_tokens = self.token_counter.count_tokens(messages)

        if total_tokens <= self.MAX_TOKENS:
            return self._generate_single_message(messages, detail_level)

        # Try splitting into chunks if exceeds token limit
        for num_chunks in range(2, self.MAX_CHUNKS + 1):
            diff_chunks = self._split_diff(diff, num_chunks)
            max_chunk_tokens = max(
                self.token_counter.count_tokens(
                    self._create_messages(system_prompt, chunk)
                )
                for chunk in diff_chunks
            )

            if max_chunk_tokens <= self.MAX_TOKENS:
                return self._generate_chunked_messages(system_prompt, diff_chunks, detail_level)

        # If we reach here, even MAX_CHUNKS wasn't enough
        console.print("Warning: Your changes are extensive. The commit message generation might be incomplete. "
              "We'll process a reduced subset of changes. This limitation will be addressed in future updates.🥹🥹🥹")
        
        # Process only the first portion that fits within token limits
        reduced_diff = []
        current_tokens = 0
        for item in diff:
            messages = self._create_messages(system_prompt, [item])
            if current_tokens + self.token_counter.count_tokens(messages) > self.MAX_TOKENS:
                break
            reduced_diff.append(item)
            current_tokens = self.token_counter.count_tokens(self._create_messages(system_prompt, reduced_diff))

        return self._generate_single_message(self._create_messages(system_prompt, reduced_diff), detail_level)

    def _generate_single_message(self, messages: List[Dict[str, str]], detail_level: str) -> str:
        max_tokens = {
            'detailed': 500,
            'brief': 200,
            'minimal': 100
        }

        if self.provider == AIProvider.OPENAI:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens[detail_level],
                n=1,
                temperature=0.7,
            )
            return completion.choices[0].message.content.strip()
        else:
            raise ValueError("Unsupported AI provider")

    def _generate_chunked_messages(self, system_prompt: str, diff_chunks: List[Union[Dict[str, str], List[Dict[str, str]]]], detail_level: str) -> str:
        all_messages = []
        for chunk in diff_chunks:
            messages = self._create_messages(system_prompt, chunk)
            message = self._generate_single_message(messages, detail_level)
            all_messages.append(message)
        
        return "\n\n".join(all_messages)