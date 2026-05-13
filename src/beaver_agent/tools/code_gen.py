"""Beaver Agent Code Generation Tool"""

from typing import Optional

import structlog

from beaver_agent.tools.file_tool import FileTool

logger = structlog.get_logger()

__all__ = ["CodeGenTool"]

# Supported languages for code generation
SUPPORTED_LANGUAGES = frozenset({
    "python", "javascript", "typescript", "go", "rust", "java",
    "c", "cpp", "c#", "csharp", "ruby", "php", "swift", "kotlin",
    "shell", "bash", "sql", "html", "css", "yaml", "json", "toml",
})

# Language aliases
_LANG_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "golang": "go",
    "rb": "ruby",
    "sh": "shell",
    "cs": "csharp",
    "py": "python",
}


class CodeGenTool:
    """Tool for generating code using LLM"""

    def __init__(self, config, llm_client):
        """Initialize the CodeGenTool.

        Args:
            config: Application configuration object.
            llm_client: LLM client instance for code generation.
        """
        self.config = config
        self.llm = llm_client
        self._file_tool = FileTool(config)

    def generate(
        self,
        description: str,
        language: str = "python",
        file_path: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """Generate code based on a description.

        Args:
            description: Natural language description of the code to generate.
            language: Programming language (python, javascript, go, etc.).
            file_path: Optional path to save the generated code.
            context: Optional additional context or requirements for generation.

        Returns:
            Generated code string, or a skeleton template if LLM is not configured.
        """
        language = self._normalize_language(language)
        logger.info("generating_code", language=language, description=description[:50])

        try:
            response = self.llm.generate_code(
                description=description, language=language, context=context
            )

            if not response.content or "not configured" in response.content:
                return self._generate_skeleton(description, language)

            if file_path:
                try:
                    save_result = self._file_tool.write_file(file_path, response.content)
                    return f"{response.content}\n\n---\n{save_result}"
                except Exception as e:
                    logger.error("code_save_failed", file_path=file_path, exc_info=e)
                    return f"{response.content}\n\n❌ Save failed: {e}"

            return response.content

        except Exception as e:
            logger.error("code_generation_failed", language=language, exc_info=e)
            return "❌ Code generation failed. Check logs for details."

    def _normalize_language(self, language: str) -> str:
        """Normalize language name (aliases, lowercasing)."""
        lang = language.lower().strip()
        return _LANG_ALIASES.get(lang, lang)

    def _generate_skeleton(self, description: str, language: str) -> str:
        """Generate code skeleton without LLM."""

        templates = {
            "python": '''# Python Code for: {description}

# This is a placeholder - configure LLM API key for full generation
# Set MINIMAX_API_KEY in .env for full generation

def main() -> None:
    """CLI entry point for code generation tool.

    When run directly, loads configuration and provides a simple REPL
    for generating code from natural language descriptions.

    Returns:
        None. Exits with status 0 on normal completion.
    """
    pass

if __name__ == "__main__":
    main()
''',
            "javascript": '''// JavaScript/Node.js for: {description}

// This is a placeholder - configure MINIMAX_API_KEY for full generation

function main() {{
    // Your implementation here
}}

module.exports = {{ main }};
''',
            "go": '''// Go code for: {description}

// This is a placeholder - configure MINIMAX_API_KEY for full generation

package main

func main() {{
    // Your implementation here
}}
''',
            "typescript": '''// TypeScript for: {description}

// This is a placeholder - configure MINIMAX_API_KEY for full generation

export function main() {{
    // Your implementation here
}}
''',
            "rust": '''// Rust code for: {description}

// This is a placeholder - configure MINIMAX_API_KEY for full generation

fn main() {{
    // Your implementation here
}}
''',
            "java": '''// Java code for: {description}

// This is a placeholder - configure MINIMAX_API_KEY for full generation

public class Main {{
    public static void main(String[] args) {{
        // Your implementation here
    }}
}}
''',
            "shell": '''#!/bin/bash
# Shell script for: {description}

# This is a placeholder - configure MINIMAX_API_KEY for full generation

set -e

main() {{
    # Your implementation here
}}

main "$@"
''',
            "sql": '''-- SQL for: {description}

-- This is a placeholder - configure MINIMAX_API_KEY for full generation

-- Your SQL here
''',
        }

        if language in templates:
            return templates[language].format(description=description)

        return "// Code for: {description}\n// Configure MINIMAX_API_KEY in .env for full generation".format(
            description=description
        )

    def complete_code(
        self, partial_code: str, description: str, language: str = "python"
    ) -> str:
        """Complete partial code by filling in TODO sections via LLM.

        Args:
            partial_code: The existing code with TODO markers to fill in.
            description: Description of what the code should do.
            language: Programming language of the code.

        Returns:
            Completed code with TODO sections filled in, or error message on failure.
        """
        language = self._normalize_language(language)
        logger.info("completing_code", language=language, description=description[:50])

        prompt_text = (
            f"Complete the following {language} code.\n"
            f"Fill in the TODO sections and complete any unfinished functions.\n\n"
            f"Description: {description}\n\n"
            f"```{language}\n{partial_code}\n```"
        )

        try:
            response = self.llm.chat(prompt_text)
            return response.content
        except Exception as e:
            logger.error("code_completion_failed", language=language, exc_info=e)
            return "❌ Code completion failed. Check logs for details."

    def refactor(
        self, code: str, style: str = "clean", language: str = "python"
    ) -> str:
        """Refactor code to follow best practices using LLM.

        Args:
            code: The source code to refactor.
            style: Refactoring style (e.g., "clean", "readable", "performant").
            language: Programming language of the code.

        Returns:
            Refactored code string, or error message on failure.
        """
        language = self._normalize_language(language)
        logger.info("refactoring_code", language=language, style=style)

        prompt_text = (
            f"Refactor the following {language} code to be more {style}.\n\n"
            f"```{language}\n{code}\n```"
        )

        try:
            response = self.llm.chat(prompt_text)
            return response.content
        except Exception as e:
            logger.error("code_refactor_failed", language=language, style=style, exc_info=e)
            return "❌ Refactoring failed. Check logs for details."
