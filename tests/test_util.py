# -*- coding: utf-8 -*-
import pytest

from voc4cat.util import Node, build_from_narrower, build_tree

text1 = """
a1
 b1
  c1
   L1
"""
expected1 = {"root": [{"a1": [{"b1": [{"c1": ["L1"]}]}]}]}
narrower1 = {"root": ["a1"], "a1": ["b1"], "b1": ["c1"], "c1": ["L1"], "L1": []}

text2 = """
a1
a2
 L1
 L2
 b1
  L3
  L4
 b2
  L5
a3
"""
expected2 = {
    "root": ["a1", {"a2": ["L1", "L2", {"b1": ["L3", "L4"]}, {"b2": ["L5"]}]}, "a3"]
}

narrower2 = {
    "root": ["a1", "a2", "a3"],
    "a1": [],
    "a2": ["L1", "L2", "b1", "b2"],
    "L1": [],
    "L2": [],
    "b1": ["L3", "L4"],
    "L3": [],
    "L4": [],
    "b2": ["L5"],
    "L5": [],
    "a3": [],
}


def test_text1():
    tree = build_tree(text1)
    expected_text = """root
a1
..b1
....c1
......L1
""".split()
    # print("n=", tree.as_narrower_dict())
    assert tree.as_dict() == expected1
    assert tree.as_indented_text(sep="..") == expected_text
    # assert tree.as_narrower_dict() == narrower1


def test_text2():
    tree = build_tree(text2)
    expected_text = """root
a1
a2
-L1
-L2
-b1
--L3
--L4
-b2
--L5
a3
""".split()
    assert tree.as_dict() == expected2
    assert tree.as_indented_text(sep="-") == expected_text
    assert tree.as_narrower_dict() == narrower2


def test_text2_reordered():
    text2 = """
a2
 b2
  L5
 L2
 L1
 b1
  L4
  L3
a3
a1
"""
    tree = build_tree(text2)
    assert tree.as_dict() == expected2
    assert tree.as_narrower_dict() == narrower2


def test_from_narrower():
    assert build_from_narrower(narrower1).as_dict() == expected1
    assert build_from_narrower(narrower2).as_dict() == expected2


def test_order_narrower():
    rev_narrower1 = dict(reversed(list(narrower1.items())))
    assert build_from_narrower(rev_narrower1).as_dict() == expected1
    rev_narrower2 = dict(reversed(list(narrower2.items())))
    assert build_from_narrower(rev_narrower2).as_dict() == expected2


def test_from_narrower_no_root():
    n = {"a1": ["a2"], "a2": ["a1"]}
    with pytest.raises(ValueError) as excinfo:
        build_from_narrower(n)
    assert "No root found on root level." in str(excinfo.value)


# def test_from_narrower_more_roots():
#     n = {"a1": [], "a2": []}
#     with pytest.raises(ValueError) as excinfo:
#         build_from_narrower(n)
#     assert "More than one node on root level found." in str(excinfo.value)


def test_narrower3():
    n = {
        'ex:1': ['ex:2', 'ex:3', 'ex:6'],
        'ex:2': [],
        'ex:3': ['ex:4', 'ex:5'],
        'ex:4': [],
        'ex:5': [],
        'ex:6': ['ex:7'],
        'ex:7': [],
        'ex:8': [],
        'ex:9': []
    }
    tree = build_from_narrower(n)
    expected = {
        'root': 0,
        'ex:1': 0,
        'ex:2': 1,
        'ex:3': 1,
        'ex:4': 2,
        'ex:5': 2,
        'ex:6': 1,
        'ex:7': 2,
        'ex:8': 0,
        'ex:9': 0
    }
    assert tree.as_level_dict() == expected


def test_from_narrower_more_roots():
    n = {"a1": [], "a2": []}
    tree = build_from_narrower(n)
    expected = {"root": ["a1", "a2"]}
    assert tree.as_dict() == expected


def test_undefined_childURI():
    n = {"a1": [], "a2": ["c"]}
    with pytest.raises(ValueError) as excinfo:
        build_from_narrower(n)
    assert 'Child "c" is not defined.' in str(excinfo.value)


def test_pure_tree():
    tree = build_tree("", sep="x")
    assert tree.children == []
    assert tree.text == "root"
    assert tree.level == 0


def test_one_node():
    text = "n1"
    tree = build_tree(text)
    expected = {"root": ["n1"]}
    assert len(tree.children) == 1
    assert tree.as_dict() == expected


def test_none_as_sep():
    text = "n1"
    tree = build_tree(text, sep=None)
    expected = {"root": ["n1"]}
    assert len(tree.children) == 1
    assert tree.as_dict() == expected


def test_bad_dedent():
    text = " x1\nx2"
    with pytest.raises(ValueError) as excinfo:
        build_tree(text)
    assert 'Level of node "x2" lower than of first node to add.' in str(excinfo.value)


def test_root_higher_level():
    tree = Node(" root")
    with pytest.raises(ValueError) as excinfo:
        tree.add_children([Node("x2")])
    assert 'Level of node "x2" lower than of root node.' in str(excinfo.value)


def test_bad_indent():
    text = "x1\n  x2"
    with pytest.raises(ValueError) as excinfo:
        build_tree(text)
    assert 'Indentation inreases by more than one level for "x2"' in str(excinfo.value)


def test_non_matching_indent_warning():
    tree = Node("root", sep="--")
    with pytest.warns(UserWarning, match='Node "-n3": Incomplete separator "--"?'):
        tree.add_children(
            [Node("n1", sep="--"), Node("--n2", sep="--"), Node("---n3", sep="--")]
        )


def test_equality():
    n1 = Node("n1")
    n2 = Node(" n2")
    assert n1 != n2
    n1.level = 1
    n2.text = "n1"
    assert n1 == n2


def test_order():
    n1 = Node("n1")
    n2 = Node("n2")
    assert n1 < n2
