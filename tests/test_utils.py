from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import Table
from voc4cat.utils import adjust_length_of_tables, split_and_tidy


def test_default_action():
    assert split_and_tidy(None) == []
    assert split_and_tidy("") == []
    assert split_and_tidy("a,b") == ["a", "b"]
    assert split_and_tidy(" a , b ") == ["a", "b"]


def test_trailing_comma():
    assert split_and_tidy("a,") == ["a"]
    assert split_and_tidy("a,b,") == ["a", "b"]


def test_expand_tables(tmp_path):
    test_wb = tmp_path / "table.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Letter", "value"])  # table header
    data = [
        ["A", 1],
        ["B", 2],
    ]
    for row in data:
        ws.append(row)
    tab = Table(displayName="Table1", ref="A1:B3")
    ws.add_table(tab)
    ws["A5"] = "X"
    wb.save(test_wb)

    adjust_length_of_tables(test_wb)

    wb = load_workbook(test_wb)
    name, table_range = wb.active.tables.items()[0]
    assert name == "Table1"
    assert table_range == "A1:B5"
