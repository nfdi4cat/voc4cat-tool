"""Tests for voc4cat.fields module."""

import pytest
from pydantic import BaseModel, HttpUrl, ValidationError

from voc4cat.fields import ORCIDIdentifier, RORIdentifier, get_orcid_id_part


@pytest.mark.parametrize(
    ("identifier", "testdata"),
    [
        # valid examples from ORCID support page
        ("0000-0002-1825-0097", "0000-0002-1825-0097"),
        ("0000-0002-1825-0097", "https://orcid.org/0000-0002-1825-0097"),
        ("0000-0002-1694-233X", "https://orcid.org/0000-0002-1694-233X"),
    ],
)
def test_orcid(identifier: str, testdata: ORCIDIdentifier) -> None:
    """Test that a model with Orcid validates correctly."""

    class Model(BaseModel):
        orcid: ORCIDIdentifier

    m = Model(orcid=testdata)

    assert m.orcid == HttpUrl(f"https://orcid.org/{identifier}")
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
        "http://0000-0001-5109-3700",  # invalid scheme, valid ORCID
        "https://0000-0002-1694-233X",  # invalid scheme, valid ORCID
    ],
)
def test_orcid_fail(testdata: ORCIDIdentifier) -> None:
    """Test invalid ORCID (wrong checksum or wrong pattern)."""

    class Model(BaseModel):
        orcid: ORCIDIdentifier

    with pytest.raises(ValidationError):
        Model(orcid=testdata)


def test_ror() -> None:
    """Test model instantiation with valid ROR id."""

    class Model(BaseModel):
        ror: RORIdentifier

    sample = "https://ror.org/02y72wh86"
    m = Model(ror=sample)  # type: ignore[call-arg]
    assert m.ror == HttpUrl(sample)


@pytest.mark.parametrize(
    "testdata",
    [
        "02y72wh86",  # not a URL
        "https://ror.org/02y72wh85",  # checksum should fail
        "https://roar.org/02y72wh86",  # wrong domain
        "https://ror.org/02y72wh86v",  ## too long id
    ],
)
def test_ror_fail(testdata: RORIdentifier) -> None:
    """Test that a pydantic model with incorrect ROR values fail."""

    class Model(BaseModel):
        ror: RORIdentifier

    with pytest.raises(ValidationError):
        Model(ror=testdata)


def test_ror_orcid_example() -> None:
    """Example usage of ORCIDIdentifier in a model."""

    class Researcher(BaseModel):
        name: str
        orcid: ORCIDIdentifier
        home_organization: RORIdentifier | None = None

        @property
        def orcid_id_part(self) -> str:
            """Get just the ID part of the ORCID identifier"""
            return get_orcid_id_part(self.orcid)

    jane = Researcher(
        name="Jane Smith",
        orcid="https://orcid.org/0000-0002-1825-0097",
        home_organization="https://ror.org/02y72wh86",
    )

    assert jane.name == "Jane Smith"
    assert jane.orcid == HttpUrl("https://orcid.org/0000-0002-1825-0097")
    assert jane.home_organization == HttpUrl("https://ror.org/02y72wh86")
    assert jane.orcid_id_part == "0000-0002-1825-0097"

    jane2 = Researcher(
        name="Jane Smith",
        orcid=HttpUrl("https://orcid.org/0000-0002-1825-0097"),
    )
    assert jane2.orcid == HttpUrl("https://orcid.org/0000-0002-1825-0097")
