"""Code to dynamically generate appropriate LLM prompts."""
import abc
import dataclasses
from typing import Union, Literal, Callable, List, Tuple

from kor.elements import Form
from kor.example_generation import simple_example_generator
from kor.type_descriptors import (
    generate_typescript_description,
)

PROMPT_FORMAT = Union[Literal["openai-chat"], Literal["string"]]


@dataclasses.dataclass(frozen=True, kw_only=True)
class PromptGenerator(abc.ABC):
    """Define abstract interface for a prompt."""

    @abc.abstractmethod
    def format_standard(self, user_input: str, form: Form) -> str:
        """Format as a prompt to a standard LLM."""
        raise NotImplementedError()

    @abc.abstractmethod
    def format_chat(self, user_input: str, form: Form) -> list[dict[str, str]]:
        """Format as a prompt to a chat model."""
        raise NotImplementedError()


@dataclasses.dataclass(frozen=True, kw_only=True)
class ExtractionTemplate(PromptGenerator):
    """Prompt generator for extraction purposes."""

    prefix: str
    type_descriptor: str
    suffix: str
    example_generator: Callable[
        [Form], List[Tuple[str, str]]
    ] = simple_example_generator

    def __post_init__(self) -> None:
        """Validate the template."""
        if self.prefix.endswith("\n"):
            raise ValueError("Please do not end the prefix with new lines.")

        if self.suffix.endswith("\n"):
            raise ValueError("Please do not end the suffix with new lines.")

    def generate_instruction_segment(self, form: Form) -> str:
        """Generate the instruction segment of the extraction."""
        type_description = generate_typescript_description(form)
        return f"{self.prefix}\n\n{type_description}\n\n{self.suffix}"

    def format_standard(self, user_input: str, form: Form) -> str:
        """Format the template for a `standard` LLM model."""
        instruction_segment = self.generate_instruction_segment(form)
        examples = self.example_generator(form)
        input_output_block = []

        for in_example, output in examples:
            input_output_block.extend(
                [
                    f"Input: {in_example}",
                    f"Output: {output}",
                ]
            )

        input_output_block.append(f"Input: {user_input}\nOutput:")
        input_output_block = "\n".join(input_output_block)
        return f"{instruction_segment}\n\n{input_output_block}"

    def format_chat(self, user_input: str, form: Form) -> list[dict[str, str]]:
        """Format the template for a `chat` LLM model."""
        instruction_segment = self.generate_instruction_segment(form)

        messages = [
            {
                "role": "system",
                "content": instruction_segment,
            }
        ]

        for example_input, example_output in self.example_generator(form):
            messages.extend(
                [
                    {"role": "user", "content": example_input},
                    {
                        "role": "assistant",
                        "content": f"{example_output}",
                    },
                ]
            )

        return messages


STANDARD_EXTRACTION_TEMPLATE = ExtractionTemplate(
    prefix=(
        "Your goal is to extract structured information from the user's input that matches "
        "the form described below. "
        "When extracting information please make sure it matches the type information exactly. "
        "IMPORTANT: For Union types the output must EXACTLY match one of the members "
        "of the Union type. "
    ),
    type_descriptor="TypeScript",
    suffix=(
        "Please enclose the extracted information in HTML style tags with the tag name "
        "corresponding to the corresponding component ID. Use angle style brackets for the "
        "tags ('>' and '<'). "
        "Only output tags when you're confident about the information that was extracted "
        "from the user's query. If you can extract several pieces of relevant information "
        'from the query, then include all of them. If "Multiple" is part '
        "of the component's type, please repeat the same tag multiple times once for "
        'each relevant extraction. If the type does not contain "Multiple" do not include it '
        "more than once."
    ),
)
