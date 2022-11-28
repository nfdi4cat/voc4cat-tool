# -*- coding: utf-8 -*-
import pytest

from voc4cat.util import (
    dag_from_indented_text,
    dag_from_narrower,
    dag_to_indented_text,
    dag_to_narrower,
    dag_to_node_levels,
)

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
    ("a2", "L1"),
    ("a2", "L2"),
    ("a2", "L2"),
    ("a2", "b1"),
    ("a2", "b2"),
    ("b1", "L3"),
    ("b1", "L4"),
    ("b2", "L5"),
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
    dag = dag_from_indented_text(text1)
    expected_text = """
a1
..b1
....c1
......L1
""".strip().split()
    assert list(dag.nodes) == nodes1
    assert set(dag.edges) == edges1
    assert dag_to_narrower(dag) == narrower1
    assert dag_to_indented_text(dag, sep="..") == expected_text


def test_text2():
    dag = dag_from_indented_text(text2)
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
    assert list(dag.nodes) == nodes2
    assert set(dag.edges) == edges2
    assert dag_to_narrower(dag) == narrower2
    assert dag_to_indented_text(dag, sep="-") == expected_text


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
    dag = dag_from_indented_text(text2_reordered)
    assert set(dag.nodes) == set(nodes2)
    assert set(dag.edges) == edges2
    assert dag_to_narrower(dag) == narrower2
    assert dag_to_indented_text(dag) == text2_reordered.strip().split("\n")


def test_from_narrower():
    dag1 = dag_from_narrower(narrower1)
    assert set(dag1.nodes) == set(nodes1)
    assert set(dag1.edges) == edges1
    dag2 = dag_from_narrower(narrower2)
    assert set(dag2.nodes) == set(nodes2)
    assert set(dag2.edges) == edges2


def test_order_narrower():
    rev_narrower1 = dict(reversed(list(narrower1.items())))
    dag1 = dag_from_narrower(rev_narrower1)
    assert set(dag1.nodes) == set(nodes1)
    assert set(dag1.edges) == edges1
    rev_narrower2 = dict(reversed(list(narrower2.items())))
    dag2 = dag_from_narrower(rev_narrower2)
    assert set(dag2.nodes) == set(nodes2)
    assert set(dag2.edges) == edges2


def test_narrower_same_concept_in_two_trees():
    n = {
        "ex:1": ["ex:2"],
        "ex:2": ["ex:3"],
        "ex:3": [],
        "ex:4": ["ex:3"],
    }
    dag = dag_from_narrower(n)
    expected = [
        ("ex:1", 0),
        ("ex:2", 1),
        ("ex:3", 2),
        ("ex:4", 0),
        ("ex:3", 1),
    ]
    assert dag_to_node_levels(dag) == expected


def test_narrower_with_cylce():
    narrower = {
        "ex:1": ["ex:2", "ex:3", "ex:6"],
        "ex:2": [],
        "ex:3": ["ex:4", "ex:5"],
        "ex:4": ["ex:1"],
        "ex:5": [],
        "ex:6": ["ex:7"],
        "ex:7": [],
        "ex:9": ["ex:7"],
        "ex:8": [],
        "ex:10": ["ex:11"],
        "ex:11": [],
    }
    expected_text = """
ex:1
  ex:2
  ex:3
    ex:4
    ex:5
  ex:6
    ex:7
ex:9
  ex:7
ex:4
  ex:1
ex:8
ex:10
  ex:11
""".strip().split(
        "\n"
    )
    expected_node_levels = [
        ("ex:1", 0),
        ("ex:2", 1),
        ("ex:3", 1),
        ("ex:4", 2),
        ("ex:5", 2),
        ("ex:6", 1),
        ("ex:7", 2),
        ("ex:9", 0),
        ("ex:7", 1),
        ("ex:4", 0),
        ("ex:1", 1),
        ("ex:8", 0),
        ("ex:10", 0),
        ("ex:11", 1),
    ]
    dag = dag_from_narrower(narrower)
    assert dag_to_node_levels(dag) == expected_node_levels
    assert dag_to_indented_text(dag, sep="  ") == expected_text


def test_from_narrower_multiple_root_nodes():
    n = {"a1": [], "a2": []}
    dag = dag_from_narrower(n)
    assert list(dag.nodes) == list(n.keys())
    assert list(dag.edges) == []


def test_redefinition_within_text():
    n = """
a1
a2
a2
-a1
"""
    dag = dag_from_indented_text(n, sep="-")
    assert list(dag.nodes) == ["a1", "a2"]
    assert list(dag.edges) == [("a2", "a1")]


def test_undefined_child():
    n = {"a1": [], "a2": ["c"]}
    with pytest.raises(ValueError) as excinfo:
        dag_from_narrower(n)
    assert 'Concept "c" needs to defined if used as narrower concept.' in str(
        excinfo.value
    )


def test_empty_text():
    dag = dag_from_indented_text("", sep="x")
    assert list(dag.nodes) == []
    assert list(dag.edges) == []


def test_one_node():
    text = "n1"
    dag = dag_from_indented_text(text)
    assert list(dag.nodes) == ["n1"]
    assert list(dag.edges) == []


def test_none_as_sep():
    text = "n1"
    dag = dag_from_indented_text(text, sep=None)
    assert list(dag.nodes) == ["n1"]
    assert list(dag.edges) == []


def test_bad_dedent():
    text = " x1\nx2"
    with pytest.raises(ValueError) as excinfo:
        dag_from_indented_text(text)
    assert 'First line "x1" must be at lowest indentation level.' in str(excinfo.value)


def test_bad_indent():
    text = "x1\n--x2"
    with pytest.raises(ValueError) as excinfo:
        dag_from_indented_text(text, sep="-")
    assert 'Indentation inreases by more than one level for "x2"' in str(excinfo.value)


def test_non_matching_indent_warning():
    text = "n1\n--n2\n---n3"
    with pytest.warns(UserWarning, match='Line "-n3": Incomplete separator "--"?'):
        dag_from_indented_text(text, sep="--")


def test_small_cylce_warning():
    n = {"a1": ["a2"], "a2": ["a1"]}
    dag = dag_from_narrower(n)
    with pytest.warns(UserWarning, match="Small unbreakable cycle detected: "):
        dag_to_node_levels(dag)
