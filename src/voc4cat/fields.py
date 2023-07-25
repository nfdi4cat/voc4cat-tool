"""Custom model fields for pydantic

- Ror (Research Organization Registry)
- ORCID (Open Researcher and Contributor ID)
"""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar, Generator

import base32_crockford
from pydantic import BaseConfig, HttpUrl
from pydantic.errors import UrlError
from pydantic.fields import ModelField
from pydantic.typing import AnyCallable

__all__ = ["Orcid", "OrcidError"]

logger = logging.getLogger(__name__)

ORCID_PATTERN = re.compile(
    r"(?P<identifier>[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]{1})$"
)


class OrcidError(UrlError):
    code = "orcid"
    msg_template = "invalid ORCiD"


class Orcid(HttpUrl):
    """
    ORCID in URL representation as model field for Pydantic.

    The validator enforces compliance with the ORCID guidelines [1]. This
    includes validation of the checksum. An ORCID given as string is converted
    to the corresponding URL form.

    [1]  ORCID Support, [Structure of the ORCID Identifier](https://support.orcid.org/hc/en-us/articles/360006897674), accessed 2023-02-22.
    """

    allowed_schemes: ClassVar[set(str)] = {"https"}

    @classmethod
    def __get_validators__(cls) -> Generator[AnyCallable, None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, field: ModelField, config: BaseConfig) -> Orcid:
        # Important if pydantic config has validate_assignment set to True
        if value.__class__ == cls:  # pragma: no cover
            return value

        m = ORCID_PATTERN.search(value)
        if not m:
            msg = "Value does not match ORCID pattern."
            raise OrcidError(msg)

        identifier = m["identifier"]
        if not cls.verify_checksum(identifier):
            msg = "Invalid ORCID checksum."
            raise OrcidError(msg)

        return HttpUrl.validate(f"https://orcid.org/{identifier}", field, config)

    @staticmethod
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


# ===  ROR (Research Organization Registry) identifier field ===

ROR_PATTERN = re.compile(
    r"https://ror.org\/(?P<identifier>0[0-9a-hj-km-np-tv-z]{6}[0-9]{2})$"
)


class RorError(UrlError):
    code = "ror"
    msg_template = "invalid ROR"


class Ror(HttpUrl):
    """
    ROR (Research Organization Registry) identifier model field for pydantic.

    ROR identifier are represented as URL. Validation is implemented according
    to the documentation and includes checksum verification [1].

    [1] Research Organization Registry, [ROR identifier pattern](https://ror.readme.io/docs/ror-identifier-pattern), April 2023.
    """

    allowed_schemes: ClassVar[set(str)] = {"https"}

    @classmethod
    def __get_validators__(cls) -> Generator[AnyCallable, None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any, field: ModelField, config: BaseConfig) -> Ror:
        # Important if pydantic config has validate_assignment set to True
        if value.__class__ == cls:  # pragma: no cover
            return value

        m = ROR_PATTERN.search(value)
        if not m:
            msg = "Value does not match ROR pattern."
            raise RorError(msg)

        identifier = m["identifier"]
        id_value = base32_crockford.decode(
            identifier[:-2]
        )  # last two digits are checksum
        checksum = str(98 - ((id_value * 100) % 97)).zfill(2)

        if checksum != identifier[-2:]:
            msg = "Invalid ROR checksum."
            raise RorError(msg)

        return HttpUrl.validate(value, field, config)
