"""Future DeepSeek route descriptor. This pilot provides no live transport."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DeepSeekRoute:
    endpoint: str = "https://api.deepseek.com/chat/completions"
    model: str = "deepseek-flash"
    max_input_tokens: int = 10_000
    max_output_tokens: int = 450
    thinking: str = "disabled"

    def __call__(self, mode, payload):
        raise RuntimeError("Live DeepSeek requires a separate authorized implementation")
