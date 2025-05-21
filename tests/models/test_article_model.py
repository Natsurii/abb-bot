"""Copyright (c) 2025 Natsurii.

Created Date: Sunday, April 27th 2025, 4:54:09 pm
Author: Natsurii

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
contributors may be used to endorse or promote products derived from this
software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS AS
IS AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
THE POSSIBILITY OF SUCH DAMAGE.

HISTORY:
Date      	By	Comments
----------	---	----------------------------------------------------------
2025-04-27	NAT	Initial test
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.models.article import Article


def test_passes_object_creation() -> None:
    """Test successful object creation of Article model."""
    model: Article = Article(title="Test", author="Test", content="Test")
    assert isinstance(model, Article)


def test_fails_validation_error() -> None:
    """Test that missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        Article()


def test_invalid_url_raises_validation_error() -> None:
    """Test that an invalid URL raises a ValidationError."""
    with pytest.raises(ValidationError):
        Article(
            title="Test Title",
            author="Test Author",
            content="Test Content",
            url="invalid-url",
        )


def test_invalid_uuid_raises_validation_error() -> None:
    """Test that an invalid UUID for id raises ValidationError."""
    with pytest.raises(ValidationError):
        Article(
            id="not-a-valid-uuid",
            title="Test Title",
            author="Test Author",
            content="Test Content",
        )


def test_default_id_is_uuid() -> None:
    """Test that the default id is generated and is a UUID."""
    model: Article = Article(title="Title", author="Author", content="Content")
    assert isinstance(model.id, type(uuid4()))


def test_tags_defaults_to_empty_list() -> None:
    """Test that tags default to an empty list."""
    model: Article = Article(title="Title", author="Author", content="Content")
    assert model.tags == []


def test_summary_can_be_none() -> None:
    """Test that summary can be explicitly set to None."""
    model: Article = Article(
        title="Test",
        author="Test",
        content="Test",
        summary=None,
    )
    assert model.summary is None


def test_custom_tags_assignment() -> None:
    """Test assigning a list of tags."""
    tags = ["python", "testing", "pydantic"]
    model: Article = Article(
        title="Tagged Article",
        author="Author",
        content="Content",
        tags=tags,
    )
    assert model.tags == tags


def test_published_at_accepts_datetime() -> None:
    """Test that published_at accepts a valid datetime."""
    publish_time = datetime.now(tz=UTC) + timedelta(
        days=1,
    )  # Future date
    model: Article = Article(
        title="Future Article",
        author="Author",
        content="Content",
        published_at=publish_time,
    )
    assert model.published_at == publish_time


def test_valid_url_passes() -> None:
    """Test that a correct URL passes validation."""
    model: Article = Article(
        title="Test URL",
        author="Test",
        content="Test",
        url="https://example.com",
    )
    assert str(model.url) == "https://example.com/"


def test_empty_strings_are_accepted() -> None:
    """Test that empty strings for title, author, and content are accepted."""
    model: Article = Article(
        title="",
        author="",
        content="",
    )
    assert model.title == ""
    assert model.author == ""
    assert model.content == ""
