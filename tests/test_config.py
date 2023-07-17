"""Tests for voc4cat.config module."""

import pytest
from pydantic import BaseModel, ValidationError


def test_imort():
    from voc4cat import config

    assert config.idranges

