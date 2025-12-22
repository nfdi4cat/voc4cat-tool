"""pydantic 2.x custom types for ORCID and ROR identifiers"""
# The approach here follows the path suggest in Pydantic documentation (2.11).
# https://docs.pydantic.dev/latest/concepts/types/#summary

import logging
import re
from typing import Annotated

import base32_crockford
from pydantic import AfterValidator, BeforeValidator, HttpUrl

__all__ = [
    "ORCIDIdentifier",
    "RORIdentifier",
]

logger = logging.getLogger(__name__)

# ===  ORCID (Open Researcher and Contributor ID) validator ===

ORCID_PATTERN = re.compile(
    r"(?P<identifier>[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]{1})$"
)
ORCID_URL = "https://orcid.org/"


def get_orcid_id_part(orcid_url: HttpUrl) -> str:
    """Extract just the identifier part from an ORCID URL."""
    return str(orcid_url).replace(ORCID_URL, "")


def normalize_orcid_input(v: str | HttpUrl) -> str:
    """
    Normalize ORCID input to a string URL format.

    Accepts:
    - Full ORCID URLs: "https://orcid.org/0000-0002-1825-0097"
    - Just the ID part: "0000-0002-1825-0097"
    - HttpUrl objects

    Returns: Full ORCID URL as string
    """
    if isinstance(v, HttpUrl):
        return str(v)

    if isinstance(v, str):  # pragma: no branch
        v = v.strip()
        if v.startswith(ORCID_URL):
            return v

        # If it's just the ID part with hyphens: 0000-0002-1825-0097
        if ORCID_PATTERN.match(v):
            return ORCID_URL + v
    # If we can't normalize it, return as-is and let validation catch the error
    return str(v)


def validate_orcid_url(value: str) -> HttpUrl:
    """Check an ORCiD URL for validity.

    The validator enforces compliance with the ORCID guidelines [1]. This
    includes validation of the checksum. An ORCID given as string is converted
    to the corresponding URL form.

    Raises
    ------
    ValueError
        Raised if the URL is not a valid ORCID URL.

    [1]  ORCID Support, [Structure of the ORCID Identifier](https://support.orcid.org/hc/en-us/articles/360006897674), accessed 2023-02-22.
    """
    m = ORCID_PATTERN.search(str(value))
    if not m:
        msg = "Value does not match ORCID pattern."
        raise ValueError(msg)

    identifier = m["identifier"]
    if not verify_checksum(identifier):
        msg = "Invalid ORCID checksum."
        raise ValueError(msg)

    return HttpUrl(ORCID_URL + identifier)


def verify_checksum(identifier: str) -> bool:
    """
    Verify checksum of ORCID identifier string
    """
    total: int = 0
    for digit in identifier[
        :-1
    ]:  # exclude the check-digit (last digit or X at the end)
        if not digit.isdigit():
            continue
        total = (total + int(digit)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    checkdigit = 10 if identifier[-1] == "X" else int(identifier[-1])
    return result == checkdigit


# Create type for ORCID identifier
ORCIDIdentifier = Annotated[
    HttpUrl, BeforeValidator(normalize_orcid_input), AfterValidator(validate_orcid_url)
]

# ===  ROR (Research Organization Registry) validator ===

ROR_PATTERN = re.compile(
    r"https://ror.org\/(?P<identifier>0[0-9a-hj-km-np-tv-z]{6}[0-9]{2})$",
    re.IGNORECASE,
)


def validate_ror_url(url_str: HttpUrl) -> HttpUrl:
    """Check a ROR URL for validity.

    ROR identifier are represented as URL. Validation is implemented according
    to the documentation and includes checksum verification [1].

    Raises
    ------
    ValueError
        Raised if the URL is not a valid ROR URL.

    [1] Research Organization Registry, [ROR identifier pattern](https://ror.readme.io/docs/ror-identifier-pattern), April 2023.
    """
    m = ROR_PATTERN.search(str(url_str))
    if not m:
        msg = "Value does not match ROR pattern."
        raise ValueError(msg)

    identifier = m["identifier"]
    id_value = base32_crockford.decode(identifier[:-2])  # last two digits are checksum
    checksum = str(98 - ((id_value * 100) % 97)).zfill(2)

    if checksum != identifier[-2:]:
        msg = "Invalid ROR checksum."
        raise ValueError(msg)

    return HttpUrl(url_str)


# Create type for ROR identifier
RORIdentifier = Annotated[HttpUrl, AfterValidator(validate_ror_url)]


if __name__ == "__main__":
    # Example usage of ORCIDIdentifier in a Pydantic model
    from pydantic import BaseModel

    class Researcher(BaseModel):
        name: str
        orcid: ORCIDIdentifier
        home_organization: RORIdentifier

        @property
        def orcid_id_part(self) -> str:
            """Get just the ID part of the ORCID identifier"""
            return get_orcid_id_part(self.orcid)

    jane = Researcher(
        name="Jane Smith",
        orcid="https://orcid.org/0000-0002-1825-0097",
        home_organization="https://ror.org/02y72wh86",
    )
    print(f"Researcher    : {jane.name}")
    print(f"ORCID ID part : {jane.orcid_id_part}")
    print(f"Full ORCID URL: {jane.orcid}")
    print(f"ROR home orga.: {jane.home_organization}")
