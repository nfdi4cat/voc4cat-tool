# -*- coding: utf-8 -*-
import pytest

from voc4cat.util import dag_from_indented_text, dag_to_indented_text, dag_from_narrower, dag_to_narrower


text1 = """
a1
 b1
  c1
   L1
"""
nodes1 = ["a1", "b1", "c1", "L1"]
edges1 = {("a1", "b1"), ("b1", "c1"), ("c1", "L1")}
narrower1 = {"a1": ["b1"], "b1": ["c1"], "c1": ["L1"], "L1": []}

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
nodes2 = ["a1", "a2", "L1", "L2", "b1", "L3", "L4", "b2", "L5", "a3"]
edges2 = {
    ("a2", "L1"), ("a2", "L2"), ("a2", "L2"), ("a2", "b1"),
    ("a2", "b2"), ("b1", "L3"), ("b1", "L4"), ("b2", "L5"),
}
narrower2 = {
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
    tree = dag_from_indented_text(text1)
    expected_text = """
a1
..b1
....c1
......L1
""".strip().split()
    assert list(tree.nodes) == nodes1
    assert set(tree.edges) == edges1
    assert dag_to_narrower(tree) == narrower1
    assert dag_to_indented_text(tree, sep="..") == expected_text


def test_text2():
    tree = dag_from_indented_text(text2)
    expected_text = """
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
""".strip().split()
    assert list(tree.nodes) == nodes2
    assert set(tree.edges) == edges2
    assert dag_to_narrower(tree) == narrower2
    assert dag_to_indented_text(tree, sep="-") == expected_text


def test_text2_reordered():
    text2_reordered = """
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
    tree = dag_from_indented_text(text2_reordered)
    assert set(tree.nodes) == set(nodes2)
    assert set(tree.edges) == edges2
    #assert dag_to_narrower(tree) == narrower2
    assert dag_to_indented_text(tree) == text2_reordered.strip().split("\n")


def test_from_narrower():
    assert dag_from_narrower(narrower1).as_dict() == expected1
    assert dag_from_narrower(narrower2).as_dict() == expected2


def test_order_narrower():
    rev_narrower1 = dict(reversed(list(narrower1.items())))
    assert dag_from_narrower(rev_narrower1).as_dict() == expected1
    rev_narrower2 = dict(reversed(list(narrower2.items())))
    assert dag_from_narrower(rev_narrower2).as_dict() == expected2


def test_from_narrower_no_root():
    n = {"a1": ["a2"], "a2": ["a1"]}
    with pytest.raises(ValueError) as excinfo:
        dag_from_narrower(n)
    assert "No root found on root level." in str(excinfo.value)


# def test_from_narrower_more_roots():
#     n = {"a1": [], "a2": []}
#     with pytest.raises(ValueError) as excinfo:
#         dag_from_narrower(n)
#     assert "More than one node on root level found." in str(excinfo.value)


def test_narrower3():
    n = {
        "ex:1": ["ex:2", "ex:3", "ex:6"],
        "ex:2": [],
        "ex:3": ["ex:4", "ex:5"],
        "ex:4": [],
        "ex:5": [],
        "ex:6": ["ex:7"],
        "ex:7": [],
        "ex:8": [],
        "ex:9": [],
    }
    tree = dag_from_narrower(n)
    expected = {
        "root": 0,
        "ex:1": 0,
        "ex:2": 1,
        "ex:3": 1,
        "ex:4": 2,
        "ex:5": 2,
        "ex:6": 1,
        "ex:7": 2,
        "ex:8": 0,
        "ex:9": 0,
    }
    assert tree.as_level_dict() == expected


def test_narrower_same_concept_in_two_trees():
    n = {
        "ex:1": ["ex:2"],
        "ex:2": ["ex:3"],
        "ex:3": [],
        "ex:4": ["ex:3"],
    }
    tree = dag_from_narrower(n)
    expected = {
        "root": 0,
        "ex:1": 0,
        "ex:2": 1,
        "ex:3": 2,
        "ex:4": 0,
        "ex:3": 1,
    }
    assert tree.as_level_dict() == expected


# def test_narrower_repeats():
#     n = {
# 'ex:1': ['ex:2', 'ex:3', 'ex:6'],
# 'ex:2': [],
# 'ex:3': ['ex:4', 'ex:5'],
# 'ex:4': ['ex:1'],
# 'ex:5': [],
# 'ex:6': ['ex:7'],
# 'ex:7': [],
# 'ex:8': [],
# 'ex:9': ['ex:7'],
# 'ex:10': ['ex:11'],
# 'ex:11': [],
#     }
#     tree = dag_from_narrower(n)
#     expected = {
#         'root': 0,
#         'ex:1': 0,
#         'ex:2': 1,
#         'ex:3': 1,
#         'ex:4': 2,
#         'ex:5': 2,
#         'ex:6': 1,
#         'ex:7': 2,
#         'ex:8': 0,
#         'ex:9': 0,
#         'ex:7': 1,
#         'ex:4': 0,
#         'ex:1': 1,
#     }
#     assert tree.as_level_dict() == expected


def test_from_narrower_more_roots():
    n = {"a1": [], "a2": []}
    tree = dag_from_narrower(n)
    expected = {"root": ["a1", "a2"]}
    assert tree.as_dict() == expected


def test_undefined_childURI():
    n = {"a1": [], "a2": ["c"]}
    with pytest.raises(ValueError) as excinfo:
        dag_from_narrower(n)
    assert 'Child "c" is not defined.' in str(excinfo.value)


def test_pure_tree():
    tree = dag_from_indented_text("", sep="x")
    assert tree.children == []
    assert tree.text == "root"
    assert tree.level == 0


def test_one_node():
    text = "n1"
    tree = dag_from_indented_text(text)
    expected = {"root": ["n1"]}
    assert len(tree.children) == 1
    assert tree.as_dict() == expected


def test_none_as_sep():
    text = "n1"
    tree = dag_from_indented_text(text, sep=None)
    expected = {"root": ["n1"]}
    assert len(tree.children) == 1
    assert tree.as_dict() == expected


def test_bad_dedent():
    text = " x1\nx2"
    with pytest.raises(ValueError) as excinfo:
        dag_from_indented_text(text)
    assert 'Level of node "x2" lower than of first node to add.' in str(excinfo.value)


def test_root_higher_level():
    tree = Node(" root")
    with pytest.raises(ValueError) as excinfo:
        tree.add_children([Node("x2")])
    assert 'Level of node "x2" lower than of root node.' in str(excinfo.value)


def test_bad_indent():
    text = "x1\n  x2"
    with pytest.raises(ValueError) as excinfo:
        dag_from_indented_text(text)
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
