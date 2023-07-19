"""Tests for voc4cat.fields module."""

import pytest
from pydantic import BaseModel, ValidationError
from voc4cat.fields import Orcid, Ror


@pytest.mark.parametrize(
    ("identifier", "testdata"),
    [
        # valid examples from ORCID support page
        ("0000-0002-1825-0097", "0000-0002-1825-0097"),
        ("0000-0002-1825-0097", "https://orcid.org/0000-0002-1825-0097"),
        ("0000-0002-1694-233X", "https://orcid.org/0000-0002-1694-233X"),
        # invalid schemes variation, valid ORCID
        ("0000-0001-5109-3700", "http://0000-0001-5109-3700"),
        ("0000-0002-1694-233X", "https://0000-0002-1694-233X"),
    ],
)
def test_orcid(identifier: str, testdata: str) -> None:
    """Test that a model with Orcid validates correctly."""

    class Model(BaseModel):
        orcid: Orcid

    m = Model(orcid=testdata)

    assert m.orcid == f"https://orcid.org/{identifier}"
    assert m.orcid.path == f"/{identifier}"
    assert m.orcid.host == "orcid.org"
    assert m.orcid.scheme == "https"


@pytest.mark.parametrize(
    "testdata",
    [
        "0000-0002-1825-0096",  # checksum wrong
        "0000-0002-1825-00971",  # id correct, formatting wrong
        "0000-00021825-0097",  # id correct, formatting wrong
        "X000-0002-1825-0096",  # X at wrong place, checksum alg correct?
    ],
)
def test_orcid_fail(testdata: str) -> None:
    """Test invalid ORCID (wrong checksum or wrong pattern)."""

    class Model(BaseModel):
        orcid: Orcid

    with pytest.raises(ValidationError):
        Model(orcid=testdata)


def test_ror() -> None:
    """Test model instantiation with valid ROR id."""

    class Model(BaseModel):
        ror: Ror

    sample = "https://ror.org/02y72wh86"
    m = Model(ror=sample)
    assert m.ror == sample


@pytest.mark.parametrize(
    "testdata",
    [
        "02y72wh86",  # not a URL
        "https://ror.org/02y72wh85",  # checksum should fail
        "https://roar.org/02y72wh86",  # wrong domain
        "https://ror.org/02y72wh86v",  ## too long id
    ],
)
def test_ror_fail(testdata: str) -> None:
    """Test that a pydantic model with incorrect ROR values fail."""

    class Model(BaseModel):
        ror: Ror

    with pytest.raises(ValidationError):
        Model(ror=testdata)
