import pytest

from app.llm.base import parse_json_object


def test_parses_plain_object():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_unwraps_single_element_array():
    # The exact failure mode observed against a real local model (qwen2.5:3b): it wrapped
    # the requested object in a one-element array instead of returning the object directly.
    assert parse_json_object('[{"a": 1}]') == {"a": 1}


def test_rejects_multi_element_array():
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_json_object('[{"a": 1}, {"b": 2}]')


def test_rejects_scalar():
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_json_object('"just a string"')


def test_rejects_array_of_non_dicts():
    with pytest.raises(ValueError, match="Expected a JSON object"):
        parse_json_object("[1, 2, 3]")
