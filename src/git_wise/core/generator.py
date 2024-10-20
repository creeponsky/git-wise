from enum import Enum
from openai import OpenAI
from git_wise.config import get_api_key
from typing import Dict, Any, List, Union, Tuple
import tiktoken
from rich.console import Console
from rich.text import Text
from git_wise.models.git_models import Language, DetailLevel, Model

console = Console()

class AIProvider(Enum):
    OPENAI = "openai"
    # TODO: add more providers. like:
    # - github copilot
    # - claude
    # - ...?

class TokenCounter:
    def __init__(self, model: str = Model.GPT4O_MINI.value[1]):
        self.encoding: tiktoken.Encoding = tiktoken.encoding_for_model(model)
    
    def count_tokens(self, message: str) -> int:
        """Count tokens for a single message."""
        return len(self.encoding.encode(message))
    
class CommitMessageGenerator:
    # just for reduce the token consumption
    MAX_CHUNKS = 8
    MAX_TOKENS = 16000  # Setting slightly below actual limit for safety
    
    def __init__(self, provider: AIProvider, model: str = Model.GPT4O_MINI.value[1], unlimited_chunk: bool = False):
        self.provider = provider
        self.model = model
        self.client = None
        self.token_counter = TokenCounter(model)
        self.unlimited_chunk = unlimited_chunk
        self._initialize_client()

    def _initialize_client(self):
        if self.provider == AIProvider.OPENAI:
            api_key = get_api_key()
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError("Unsupported AI provider")

    def _split_message(self, message: str, max_tokens: int) -> List[str]:
        """Split the message into chunks of max_tokens."""
        return [message[i:i + max_tokens] for i in range(0, len(message), max_tokens)]

    def _create_messages(self, system_prompt: str, user_message: str) -> List[Dict[str, str]]:
        res = [{"role": "system", "content": system_prompt}]
        
        # 计算user_message 是否超过最大token限制，超过的话按照maxtoken进行拆分
        message_tokens = self.token_counter.count_tokens(user_message)
        
        if message_tokens > self.MAX_TOKENS:
             # If we reach here, even MAX_CHUNKS wasn't enough
            #TODO: In the future, we can use a more advanced method to handle this, such as separately processing long text modification files to summarize the main points of the changes, and then placing them here for a unified request again?🤔
            chunks = self._split_message(user_message, self.MAX_TOKENS)
            if len(chunks) > self.MAX_CHUNKS and not self.unlimited_chunk:
                console.print(f"[yellow]Warning: Your staged changes exceed the current token limit ({self.MAX_CHUNKS * self.MAX_TOKENS} tokens). You have {message_tokens} tokens of changes. To prevent excessive token consumption, we'll process only a subset of your changes. The commit message may not reflect all modifications. This limitation will be addressed in future updates to handle large files more effectively🥹🥹🥹.[/yellow]")
                chunks = chunks[:self.MAX_CHUNKS]
            for chunk in chunks:
                res.append({"role": "user", "content": chunk})
        else:
            res.append({"role": "user", "content": user_message})
        
        return res

    def generate_commit_message(self, diff: str, language: str, detail_level: str, repo_info: Dict[str, Any]) -> Tuple[str, int]:
        """
        Generate a commit message based on the provided diff and configuration.

        Args:
            diff (Union[Dict[str, str], List[Dict[str, str]]]): The staged changes, either as a dictionary or a list of dictionaries.
            language (str): The preferred language for the commit message.
            detail_level (str): The desired level of detail for the commit message.
            repo_info (Dict[str, Any]): Information about the repository context.

        Returns:
            str: The generated commit message.
        """
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
        return self._generate_single_message(messages)

    def _generate_single_message(self, messages: List[Dict[str, str]]) -> Tuple[str, int]:
        if self.provider == AIProvider.OPENAI:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                n=1,
                temperature=0.7,
            )

            message = completion.choices[0].message.content.strip()
            total_tokens = completion.usage.total_tokens
            return message, total_tokens
        else:
            raise ValueError("Unsupported AI provider")