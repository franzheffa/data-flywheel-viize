# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
from unittest.mock import patch

import pytest

from src.lib.integration.openai_format_validator import OpenAIFormatValidator


class TestOpenAIFormatValidator:
    """Test suite for OpenAIFormatValidator class."""

    @pytest.fixture
    def validator(self):
        """Create an OpenAIFormatValidator instance."""
        return OpenAIFormatValidator()

    @pytest.mark.parametrize(
        "record,expected",
        [
            # Valid basic chat completion format
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Hello"}]},
                    "response": {"choices": [{"message": {"content": "Hi there!"}}]},
                },
                True,
            ),
            # Valid with multiple messages
            (
                {
                    "request": {
                        "messages": [
                            {"role": "system", "content": "You are helpful"},
                            {"role": "user", "content": "Hello"},
                            {"role": "assistant", "content": "Hi!"},
                            {"role": "user", "content": "How are you?"},
                        ]
                    },
                    "response": {"choices": [{"message": {"content": "I'm doing well!"}}]},
                },
                True,
            ),
            # Valid with multiple choices
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Hello"}]},
                    "response": {
                        "choices": [
                            {"message": {"content": "Hi!"}},
                            {"message": {"content": "Hello!"}},
                        ]
                    },
                },
                True,
            ),
            # Valid with empty messages list
            (
                {
                    "request": {"messages": []},
                    "response": {"choices": []},
                },
                False,
            ),
            # Invalid - missing request
            (
                {
                    "response": {"choices": [{"message": {"content": "Hi!"}}]},
                },
                False,
            ),
            # Invalid - missing response
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Hello"}]},
                },
                False,
            ),
            # Invalid - request is not a dict
            (
                {
                    "request": "not a dict",
                    "response": {"choices": []},
                },
                False,
            ),
            # Invalid - response is not a dict
            (
                {
                    "request": {"messages": []},
                    "response": "not a dict",
                },
                False,
            ),
            # Invalid - missing messages in request
            (
                {
                    "request": {},
                    "response": {"choices": []},
                },
                False,
            ),
            # Invalid - messages is not a list
            (
                {
                    "request": {"messages": "not a list"},
                    "response": {"choices": []},
                },
                False,
            ),
            # Invalid - missing choices in response
            (
                {
                    "request": {"messages": []},
                    "response": {},
                },
                False,
            ),
            # Invalid - choices is not a list
            (
                {
                    "request": {"messages": []},
                    "response": {"choices": "not a list"},
                },
                False,
            ),
            # Invalid - empty dict
            ({}, False),
            # Invalid - None values
            (
                {
                    "request": None,
                    "response": {"choices": []},
                },
                False,
            ),
        ],
    )
    def test_validate_chat_completion_format(self, validator, record, expected):
        """Test chat completion format validation with various inputs."""
        assert validator.validate_chat_completion_format(record) == expected

    @pytest.mark.parametrize(
        "record,expected",
        [
            # No tool calls - quality check fails
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Hello"}]},
                    "response": {"choices": [{"message": {"content": "Hi!"}}]},
                },
                False,
            ),
            # Has tool_calls in message - quality check Passes
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Get weather"}]},
                    "response": {
                        "choices": [
                            {
                                "message": {
                                    "content": "I'll check the weather",
                                    "tool_calls": [
                                        {
                                            "id": "call_123",
                                            "type": "function",
                                            "function": {
                                                "name": "get_weather",
                                                "arguments": '{"location": "NYC"}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    },
                },
                True,
            ),
            # Has finish_reason as tool_calls - quality check passes
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Get weather"}]},
                    "response": {
                        "choices": [
                            {
                                "message": {"content": "Checking weather..."},
                                "finish_reason": "tool_calls",
                            }
                        ]
                    },
                },
                True,
            ),
            # Empty tool_calls list - quality check fails
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Hello"}]},
                    "response": {"choices": [{"message": {"content": "Hi!", "tool_calls": []}}]},
                },
                False,
            ),
            # None tool_calls - quality check fails
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Hello"}]},
                    "response": {"choices": [{"message": {"content": "Hi!", "tool_calls": None}}]},
                },
                False,
            ),
            # Multiple choices, one with tool calls - quality check passes
            (
                {
                    "request": {"messages": [{"role": "user", "content": "Get weather"}]},
                    "response": {
                        "choices": [
                            {"message": {"content": "Hi!"}},
                            {
                                "message": {
                                    "content": "Checking...",
                                    "tool_calls": [{"function": {"name": "get_weather"}}],
                                }
                            },
                        ]
                    },
                },
                True,
            ),
            # Invalid structure - returns True (no tool calls found)
            (
                {
                    "request": {"messages": []},
                    "response": {},
                },
                False,
            ),
        ],
    )
    def test_validate_tool_calling_quality(self, validator, record, expected):
        """Test tool calling quality validation."""
        assert validator.validate_tool_calling_quality(record) == expected

    @pytest.mark.parametrize(
        "record,has_tool_calls",
        [
            # No tool calls
            (
                {
                    "response": {"choices": [{"message": {"content": "Hi!"}}]},
                },
                False,
            ),
            # Has tool_calls array
            (
                {
                    "response": {
                        "choices": [
                            {"message": {"tool_calls": [{"function": {"name": "get_weather"}}]}}
                        ]
                    },
                },
                True,
            ),
            # Has finish_reason tool_calls
            (
                {
                    "response": {"choices": [{"finish_reason": "tool_calls"}]},
                },
                True,
            ),
            # Empty response
            ({"response": {}}, False),
            # No response key
            ({}, False),
            # Empty choices
            ({"response": {"choices": []}}, False),
            # Invalid structure handled gracefully
            ({"response": "not a dict"}, False),
        ],
    )
    def test_has_tool_calls(self, validator, record, has_tool_calls):
        """Test _has_tool_calls method."""
        assert validator._has_tool_calls(record) == has_tool_calls

    def test_parse_function_arguments_to_json(self, validator):
        """Test parsing function arguments from strings to JSON objects."""
        # Test with valid JSON string arguments
        record = {
            "response": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": '{"location": "New York", "unit": "celsius"}',
                                    }
                                },
                                {
                                    "function": {
                                        "name": "get_time",
                                        "arguments": '{"timezone": "EST"}',
                                    }
                                },
                            ]
                        }
                    }
                ]
            }
        }

        validator._parse_function_arguments_to_json(record)

        # Check that arguments were parsed to dicts
        tool_calls = record["response"]["choices"][0]["message"]["tool_calls"]
        assert tool_calls[0]["function"]["arguments"] == {
            "location": "New York",
            "unit": "celsius",
        }
        assert tool_calls[1]["function"]["arguments"] == {"timezone": "EST"}

    def test_parse_function_arguments_already_parsed(self, validator):
        """Test that already parsed arguments are not modified."""
        record = {
            "response": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": {"location": "NYC", "unit": "fahrenheit"},
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        original_args = record["response"]["choices"][0]["message"]["tool_calls"][0]["function"][
            "arguments"
        ]
        validator._parse_function_arguments_to_json(record)

        # Arguments should remain unchanged
        assert (
            record["response"]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
            == original_args
        )

    @patch("src.lib.integration.openai_format_validator.logger")
    def test_parse_function_arguments_invalid_json(self, mock_logger, validator):
        """Test handling of invalid JSON in function arguments."""
        record = {
            "response": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "get_weather",
                                        "arguments": "invalid json {",
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        validator._parse_function_arguments_to_json(record)

        # Should log warning for invalid JSON
        mock_logger.warning.assert_called_once()
        assert "Failed to parse function arguments" in mock_logger.warning.call_args[0][0]

    def test_parse_function_arguments_edge_cases(self, validator):
        """Test edge cases for parsing function arguments."""
        # Empty record
        record = {}
        validator._parse_function_arguments_to_json(record)  # Should not raise

        # No tool calls
        record = {"response": {"choices": [{"message": {}}]}}
        validator._parse_function_arguments_to_json(record)  # Should not raise

        # Empty tool calls list
        record = {"response": {"choices": [{"message": {"tool_calls": []}}]}}
        validator._parse_function_arguments_to_json(record)  # Should not raise

        # Missing function key
        record = {"response": {"choices": [{"message": {"tool_calls": [{}]}}]}}
        validator._parse_function_arguments_to_json(record)  # Should not raise

        # No arguments key
        record = {
            "response": {"choices": [{"message": {"tool_calls": [{"function": {"name": "test"}}]}}]}
        }
        validator._parse_function_arguments_to_json(record)  # Should not raise

    def test_exception_handling(self, validator):
        """Test that exceptions are handled gracefully."""
        # Test with various malformed inputs that might raise exceptions
        malformed_records = [
            None,  # None input
            "not a dict",  # String input
            [],  # List input
            {"request": {"messages": None}},  # None where list expected
            {"response": {"choices": "not a list"}},  # String where list expected
        ]

        for record in malformed_records:
            # Should not raise exceptions, just return False
            assert validator.validate_chat_completion_format(record) is False
            assert validator.validate_tool_calling_quality(record) is False  # No tool calls found

    def test_validate_with_fixtures(
        self, validator, valid_openai_record, openai_record_with_tool_calls
    ):
        """Test validation using fixture data."""
        # Valid record should pass format validation
        assert validator.validate_chat_completion_format(valid_openai_record) is True
        assert validator.validate_tool_calling_quality(valid_openai_record) is False

        # Record with tool calls should pass format but fail quality check
        assert validator.validate_chat_completion_format(openai_record_with_tool_calls) is True
        assert validator.validate_tool_calling_quality(openai_record_with_tool_calls) is True

    def test_batch_validation(self, validator, openai_records_batch):
        """Test validation of multiple records."""
        for record in openai_records_batch:
            assert validator.validate_chat_completion_format(record) is True
            assert validator.validate_tool_calling_quality(record) is False

    def test_invalid_records_from_fixtures(self, validator, invalid_openai_records):
        """Test that all invalid records fail validation."""
        for record in invalid_openai_records:
            assert validator.validate_chat_completion_format(record) is False

    def test_nested_tool_calls(self, validator):
        """Test handling of complex nested tool call structures."""
        record = {
            "request": {"messages": [{"role": "user", "content": "Complex request"}]},
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": "Processing...",
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {
                                        "name": "complex_function",
                                        "arguments": json.dumps(
                                            {
                                                "nested": {
                                                    "data": ["item1", "item2"],
                                                    "config": {"key": "value"},
                                                }
                                            }
                                        ),
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        }

        assert validator.validate_chat_completion_format(record) is True
        assert validator.validate_tool_calling_quality(record) is True

        # Parse arguments
        validator._parse_function_arguments_to_json(record)
        args = record["response"]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
        assert isinstance(args, dict)
        assert args["nested"]["data"] == ["item1", "item2"]

    def test_unicode_and_special_characters(self, validator):
        """Test handling of unicode and special characters in content."""
        record = {
            "request": {
                "messages": [
                    {"role": "user", "content": "Hello 你好 🌍 \n\t Special chars: <>&\"'"}
                ]
            },
            "response": {
                "choices": [{"message": {"content": "Response with émojis 🎉 and spëcial çhars"}}]
            },
        }

        assert validator.validate_chat_completion_format(record) is True
        assert validator.validate_tool_calling_quality(record) is False

    def test_very_large_record(self, validator):
        """Test handling of very large records."""
        # Create a record with many messages
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}" * 100}
            for i in range(100)
        ]

        record = {
            "request": {"messages": messages},
            "response": {"choices": [{"message": {"content": "Final response" * 1000}}]},
        }

        assert validator.validate_chat_completion_format(record) is True
        assert validator.validate_tool_calling_quality(record) is False

    @pytest.mark.parametrize(
        "finish_reason,expected_has_tools",
        [
            ("stop", False),
            ("length", False),
            ("tool_calls", True),
            ("function_call", False),  # Not checking for this
            (None, False),
            ("", False),
        ],
    )
    def test_finish_reason_variations(self, validator, finish_reason, expected_has_tools):
        """Test different finish_reason values."""
        record = {
            "response": {
                "choices": [
                    {
                        "message": {"content": "Response"},
                        "finish_reason": finish_reason,
                    }
                ]
            }
        }

        assert validator._has_tool_calls(record) == expected_has_tools

    def test_multiple_choices_mixed_tool_calls(self, validator):
        """Test record with multiple choices where only some have tool calls."""
        record = {
            "request": {"messages": [{"role": "user", "content": "Multi-response"}]},
            "response": {
                "choices": [
                    {"message": {"content": "Response 1"}},
                    {"message": {"content": "Response 2", "tool_calls": []}},
                    {
                        "message": {
                            "content": "Response 3",
                            "tool_calls": [{"function": {"name": "test"}}],
                        }
                    },
                    {"message": {"content": "Response 4"}},
                ]
            },
        }

        assert validator.validate_chat_completion_format(record) is True
        assert validator.validate_tool_calling_quality(record) is True  # Has tool calls

    def test_empty_string_arguments(self, validator):
        """Test handling of empty string arguments in tool calls."""
        record = {
            "response": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "test_function",
                                        "arguments": "",
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        # Should not crash on empty string
        validator._parse_function_arguments_to_json(record)
        # Empty string remains as is (not valid JSON)
        assert (
            record["response"]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
            == ""
        )

    def test_whitespace_only_arguments(self, validator):
        """Test handling of whitespace-only arguments."""
        record = {
            "response": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": "test_function",
                                        "arguments": "   \n\t   ",
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        }

        validator._parse_function_arguments_to_json(record)
        # Whitespace string remains as is
        assert (
            record["response"]["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"]
            == "   \n\t   "
        )

    @patch("src.lib.integration.openai_format_validator.logger")
    def test_parse_function_arguments_key_error(self, mock_logger, validator):
        """Test handling of KeyError/TypeError in parse function arguments."""
        # Create a record that will cause KeyError when accessing nested keys
        record = {
            "response": {
                "choices": [
                    {
                        "message": {
                            "tool_calls": "not a list"  # This will cause TypeError
                        }
                    }
                ]
            }
        }

        validator._parse_function_arguments_to_json(record)

        # Should log warning for the error
        mock_logger.warning.assert_called_once()
        assert "Error parsing function arguments" in mock_logger.warning.call_args[0][0]
