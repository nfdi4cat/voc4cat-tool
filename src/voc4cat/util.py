# -*- coding: utf-8 -*-
from operator import itemgetter
from warnings import warn

import networkx as nx


def _get_edges(text_with_level, base_level):  # noqa: WPS231
    edges = []
    level_parent_map = {}
    for concept, level in text_with_level:
        if level not in level_parent_map:  # no parent stored for this level
            level_parent_map[level] = concept
        if level == max(level_parent_map.keys()):  # a new possible parent
            level_parent_map[level] = concept
            if level > base_level:
                edges.append((level_parent_map[level - 1], concept))
        else:  # back to lower level
            # remove higher-level parents and register new parent for this level
            level_parent_map = {
                lvl: cpt for lvl, cpt in level_parent_map.items() if lvl <= level
            }
            level_parent_map[level] = concept
            if level > base_level:
                edges.append((level_parent_map[level - 1], concept))
        # print(f"concept {concept} - level_parent_map: {level_parent_map}")
    return edges


def dag_from_indented_text(text, sep=" "):
    """Build networkx directed graph from indented text."""
    # remove empty lines
    indented_lines = [line for line in text.splitlines() if line.strip()]
    text_with_level = []
    nodes = []
    for indented_line in indented_lines:
        split_line = indented_line.rstrip().split(sep)
        level = len(split_line) - 1
        concept = split_line[level]
        if concept not in nodes:
            nodes.append(concept)
        if sep is not None and len(sep) > 1 and concept.startswith(sep[0]):
            warn(f'Line "{concept}": Incomplete separator "{sep}"?')
        if text_with_level and (level - 1) > text_with_level[-1][1]:
            raise ValueError(
                f'Indentation inreases by more than one level for "{concept}".'
            )
        text_with_level.append((concept, level))

    if text_with_level:
        _, base_level = min(text_with_level, key=itemgetter(1))
        # Check if first line is at base level.
        concept, level = text_with_level[0]
        if base_level != level:
            raise ValueError(
                f'First line "{concept}" must be at lowest indentation level.'
            )
    else:
        base_level = 0

    edges = _get_edges(text_with_level, base_level)

    dag = nx.DiGraph()
    dag.add_nodes_from(nodes)
    dag.add_edges_from(edges)
    return dag


def dag_to_indented_text(termdag, sep=" "):
    """Build networkx directed graph from indented text."""
    node_levels = dag_to_node_levels(termdag)
    out = []
    for node, level in node_levels:
        out.append(level * sep + node)
    return out


def _break_cycles(dag, edges_cycle):
    # print(f"-> has cycle: {edges_cycle} - len={len(edges_cycle)}")
    if len(edges_cycle) < 3:
        warn(f'Small unbreakable cycle detected: "{edges_cycle}"')
        return ()
    # find edge to break
    deg_out = dict(dag.out_degree)
    edge_deg_diff = []
    for edge in dag.edges:
        start_node, end_node = edge
        deg_diff = deg_out[end_node] - deg_out[start_node]
        edge_deg_diff.append((edge, deg_diff))
    edge_to_break, _ = max(edge_deg_diff, key=itemgetter(1))
    # print(f"-> edge to break: {edge_to_break}")
    return edge_to_break


def _node_levels(sl, root_node, level=0, sep="  ", out=None):
    if out is None:
        out = []
    successors = sl.pop(root_node)
    out.append((root_node, level))
    for sn in successors:
        if sn in sl:

            _node_levels(sl, sn, level=level + 1, sep=sep, out=out)
        else:
            out.append((sn, level + 1))
    return out


def dag_to_node_levels(termgraph, baselevel=0):
    """Build tree representation of directed graph breaking cycles as needed."""
    subgraphs = [
        termgraph.subgraph(sgc).copy()
        for sgc in nx.connected_components(termgraph.to_undirected())
    ]
    node_levels = []
    for subgraph in subgraphs:
        # print(f"\nsubgraph: {subgraph}")
        broken_edges = []
        for cycle in nx.simple_cycles(subgraph):
            edge = _break_cycles(subgraph, cycle)
            if edge:
                broken_edges.append(edge)

        # We need a clean subgraph without cylces for creating an indented tree.
        subgraph_clean = subgraph.copy()
        subgraph_clean.remove_edges_from(broken_edges)
        roots = [node for node, degree in subgraph_clean.in_degree() if degree == 0]

        for root in roots:
            # successors in breadth-first-search
            succ_bfs = dict(nx.bfs_successors(subgraph_clean, root))
            node_levels.extend(_node_levels(succ_bfs, root, level=baselevel))

        # Add broken_edges
        for broken_edge in broken_edges:
            start_node, end_node = broken_edge
            node_levels.append((start_node, baselevel))
            node_levels.append((end_node, baselevel + 1))

    return node_levels


def dag_from_narrower(narrower):
    """Build networkx directed graph from narrower dictionary."""
    nodes = narrower.keys()
    edges = []
    for concept, children in narrower.items():
        for child in children:
            # check for undefined children
            if child not in nodes:
                raise ValueError(
                    f'Concept "{child}" needs to defined if use as narrower concept.'
                )
            edges.append((concept, child))

    dag = nx.DiGraph()
    dag.add_nodes_from(nodes)
    dag.add_edges_from(edges)
    return dag


def dag_to_narrower(dag):
    """Build children representation form networkx directed graph."""
    narrower = {}
    for node in dag.nodes:
        narrower[node] = sorted(dag.successors(node))
    return narrower
