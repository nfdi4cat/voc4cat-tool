"""Tests for voc4cat.checks module."""

import pytest
from voc4cat.checks import (
    check_for_removed_iris,
    check_number_of_files_in_inbox,
    validate_config_has_idrange,
    validate_name_of_vocabulary,
)


def test_validate_config_has_idrange():
    validate_config_has_idrange
    pass

def test_check_number_of_files_in_inbox():
    check_number_of_files_in_inbox
    pass

def test_validate_name_of_vocabulary():
    validate_name_of_vocabulary
    pass

def test_check_for_removed_iris():
    check_for_removed_iris
    pass
