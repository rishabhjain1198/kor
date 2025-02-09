"""Test that the extraction chain works as expected."""
from typing import Any, List, Mapping, Optional

import pytest
from langchain.chains import LLMChain
from langchain.chat_models.base import BaseChatModel
from langchain.schema import (
    AIMessage,
    BaseMessage,
    ChatGeneration,
    ChatResult,
)
from pydantic import Extra

from kor.encoders import CSVEncoder, JSONEncoder
from kor.extraction import create_extraction_chain
from kor.nodes import Object, Text


class ToyChatModel(BaseChatModel):
    response: str

    class Config:
        """Configuration for this pydantic object."""

        extra = Extra.forbid
        arbitrary_types_allowed = True

    def _generate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None
    ) -> ChatResult:
        message = AIMessage(content=self.response)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    def _agenerate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None
    ) -> Any:
        raise NotImplementedError()


SIMPLE_TEXT_SCHEMA = Text(
    id="text_node",
    description="Text Field",
    many=False,
    examples=[("hello", "goodbye")],
)
SIMPLE_OBJECT_SCHEMA = Object(id="obj", description="", attributes=[SIMPLE_TEXT_SCHEMA])


@pytest.mark.parametrize(
    "options",
    [
        {"encoder_or_encoder_class": "csv", "input_formatter": None},
        {"encoder_or_encoder_class": "csv", "input_formatter": "text_prefix"},
        {"encoder_or_encoder_class": "json"},
        {"encoder_or_encoder_class": "xml"},
        {"encoder_or_encoder_class": JSONEncoder()},
        {"encoder_or_encoder_class": JSONEncoder},
        {"encoder_or_encoder_class": CSVEncoder},
    ],
)
def test_create_extraction_chain(options: Mapping[str, Any]) -> None:
    """Create an extraction chain."""
    chat_model = ToyChatModel(response="hello")

    for schema in [SIMPLE_OBJECT_SCHEMA]:
        chain = create_extraction_chain(chat_model, schema, **options)
        assert isinstance(chain, LLMChain)
        # Try to run through predict and parse
        chain.predict_and_parse(text="some string")


@pytest.mark.parametrize(
    "options",
    [
        {"encoder_or_encoder_class": CSVEncoder, "node": SIMPLE_OBJECT_SCHEMA},
        {
            "encoder_or_encoder_class": CSVEncoder(SIMPLE_OBJECT_SCHEMA),
            "node": SIMPLE_OBJECT_SCHEMA,
        },
    ],
)
def test_create_extraction_chain_with_csv_encoder(options: Mapping[str, Any]) -> None:
    """Create an extraction chain."""
    chat_model = ToyChatModel(response="hello")

    chain = create_extraction_chain(chat_model, **options)
    assert isinstance(chain, LLMChain)
    # Try to run through predict and parse
    chain.predict_and_parse(text="some string")


MANY_TEXT_SCHEMA = Text(
    id="text_node",
    description="Text Field",
    many=True,
    examples=[("hello", "goodbye")],
)


OBJECT_SCHEMA_WITH_MANY = Object(
    id="obj", description="", attributes=[MANY_TEXT_SCHEMA]
)


OBJECT_SCHEMA_WITH_NESTED_OBJECT = Object(
    id="obj",
    description="",
    attributes=[Object(id="nested", attributes=[SIMPLE_TEXT_SCHEMA])],
)


@pytest.mark.parametrize(
    "options",
    [
        # Not supporting embedded lists yet
        {"encoder_or_encoder_class": CSVEncoder, "node": OBJECT_SCHEMA_WITH_MANY},
        # Not supporting nested objects yet
        {
            "encoder_or_encoder_class": CSVEncoder,
            "node": OBJECT_SCHEMA_WITH_NESTED_OBJECT,
        },
    ],
)
def test_not_implemented_assertion_raised_for_csv(options: Mapping[str, Any]) -> None:
    """Create an extraction chain."""
    chat_model = ToyChatModel(response="hello")

    with pytest.raises(NotImplementedError):
        create_extraction_chain(chat_model, **options)
