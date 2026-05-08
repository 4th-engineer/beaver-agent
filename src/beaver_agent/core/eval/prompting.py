"""Component 3: Prompting Strategy — how to construct prompts for each task type."""

from dataclasses import dataclass, field

__all__ = [
    "PromptStrategy",
    "CODE_GENERATION_STRATEGY",
    "BUG_FIX_STRATEGY",
    "CODE_REVIEW_STRATEGY",
    "ARCHITECTURE_STRATEGY",
    "STRATEGY_MAP",
    "get_strategy",
]


@dataclass
class PromptStrategy:
    """Defines how to construct prompts for a specific task type.

    Attributes:
        name: Identifier for this strategy (e.g., "code_generation", "bug_fix").
        system_template: Static system-level instructions provided to the LLM.
            Shapes the LLM's role and behavior (e.g., "You are an expert Python programmer").
        user_template: Template string for the user prompt. The literal ``{prompt}``
            placeholder is replaced with the task-specific prompt at build time.
            Defaults to ``"{prompt}"`` which passes the task text unchanged.
        few_shot_examples: Optional list of ``{input, output}`` dicts providing
            in-context examples. When non-empty, each example is formatted as
            ``"Example: {input}\\nResponse: {output}"`` and prepended to the user
            prompt before the actual task, separated by blank lines.

    Example:
        >>> strategy = PromptStrategy(
        ...     name="code_generation",
        ...     system_template="You are an expert Python programmer.",
        ...     few_shot_examples=[
        ...         {"input": "def double(x):", "output": "return x * 2"}
        ...     ]
        ... )
        >>> system, user = strategy.build("Write a function that triples a number")
        >>> print(system)
        You are an expert Python programmer.
        >>> print(user[:50])
        Example: def double(x):
    """

    name: str
    system_template: str = ""
    user_template: str = "{prompt}"
    few_shot_examples: list[dict] = field(default_factory=list)

    def build(self, task_prompt: str) -> tuple[str, str]:
        """Build (system_prompt, user_prompt) tuple from task prompt.

        Args:
            task_prompt: The task-specific prompt text (e.g., "Fix this bug in foo()").

        Returns:
            A tuple of (system_prompt, user_prompt) where system_prompt provides
            instructions to the LLM and user_prompt contains the task content.
            If few-shot examples are configured, they are prepended to the user prompt.
        """
        system = self.system_template
        user = self.user_template.format(prompt=task_prompt)

        if self.few_shot_examples:
            shots = "\n\n".join(
                f"Example: {ex['input']}\nResponse: {ex['output']}" for ex in self.few_shot_examples
            )
            user = f"{shots}\n\nNow you:\n{user}"

        return system, user


# Built-in strategies per task type

CODE_GENERATION_STRATEGY = PromptStrategy(
    name="code_generation",
    system_template=(
        "You are an expert Python programmer. Generate clean, working code "
        "based on the description. Only output the code, no explanations."
    ),
)
"""Strategy for code generation tasks — generates clean, working code from description."""

BUG_FIX_STRATEGY = PromptStrategy(
    name="bug_fix",
    system_template=(
        "You are an expert debugger. Given the error message and source code, "
        "identify the bug and provide the fixed code. Only output the fixed code."
    ),
)
"""Strategy for bug fix tasks — identifies bugs and outputs fixed code."""

CODE_REVIEW_STRATEGY = PromptStrategy(
    name="code_review",
    system_template=(
        "You are a senior code reviewer. Analyze the code and provide constructive feedback. "
        "Focus on: correctness, security, performance, and readability."
    ),
)
"""Strategy for code review tasks — analyzes code and provides feedback on quality."""

ARCHITECTURE_STRATEGY = PromptStrategy(
    name="architecture",
    system_template=(
        "You are a software architect. Design a clean, scalable architecture "
        "based on the requirements. Output a markdown description with key components."
    ),
)
"""Strategy for architecture tasks — designs scalable system architecture."""


STRATEGY_MAP: dict[str, PromptStrategy] = {
    "code_generation": CODE_GENERATION_STRATEGY,
    "bug_fix": BUG_FIX_STRATEGY,
    "code_review": CODE_REVIEW_STRATEGY,
    "architecture": ARCHITECTURE_STRATEGY,
}


def get_strategy(task_type: str) -> PromptStrategy:
    """Get the PromptStrategy for a given task type.

    Args:
        task_type: The type of task. Supported values:
            - "code_generation": Expert code generation
            - "bug_fix": Debugging and bug fixing
            - "code_review": Code review and feedback
            - "architecture": System design and architecture

    Returns:
        The PromptStrategy for the given task type, or
        CODE_GENERATION_STRATEGY as a default fallback.
    """
    return STRATEGY_MAP.get(task_type, CODE_GENERATION_STRATEGY)
