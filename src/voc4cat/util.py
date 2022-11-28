# from copy import copy
# from functools import total_ordering
# from itertools import chain
from operator import itemgetter
from warnings import warn

import networkx as nx

# @total_ordering
# class Node:
#     """
#     Node class to build a linked tree of nodes.

#     The tree can be built from

#     - indented text (the indent-seperator can be adjusted)
#     - a dictionary with node-children key-value pairs
#     """

#     def __init__(self, indented_line, sep=" "):
#         self.children = []
#         split_line = indented_line.rstrip().split(sep)
#         self.level = len(split_line) - 1
#         self.text = split_line[self.level]
#         if sep is not None and len(sep) > 1 and self.text.startswith(sep[0]):
#             warn(f'Node "{self.text}": Incomplete separator "{sep}"?')

#     def add_children(self, nodes):
#         """Add more child nodes to node."""
#         if not nodes:
#             return
#         for node in nodes:
#             if self.level > node.level:
#                 raise ValueError(
#                     f'Level of node "{node.text}" lower than of ' "root node."
#                 )
#             if nodes[0].level > node.level:
#                 raise ValueError(
#                     f'Level of node "{node.text}" lower than of ' "first node to add."
#                 )
#         # Make a copy to avoid changing nodes.
#         self.__add_children(list(nodes))

#     def __add_children(self, nodes):
#         childlevel = nodes[0].level
#         while nodes:
#             node = nodes.pop(0)
#             if node.level == childlevel:  # add node as a child
#                 self.children.append(node)
#             elif (node.level - childlevel) == 1:  # grandchildren of last child
#                 nodes.insert(0, node)
#                 if self.children:
#                     self.children[-1].__add_children(nodes)
#             elif (node.level - childlevel) > 1:
#                 raise ValueError(
#                     "Indentation inreases by more than one " f'level for "{node.text}"'
#                 )
#             elif node.level <= self.level:  # sibling, no more children
#                 nodes.insert(0, node)
#                 return

#     def add_nodes_narrower(self, narrower):
#         """Add children and their level from narrower dict."""
#         nodes = {}
#         stack = []
#         list_of_all_children = list(chain.from_iterable(list(narrower.values())))

#         # Check if all children are also key in narrower.
#         for ch in list_of_all_children:
#             if ch not in narrower.keys():
#                 raise ValueError(f'Child "{ch}" is not defined.')

#         # Create nodes that are never present as child and store in nodes.
#         # Only these nodes are fully defined at this point.
#         for nd in list(narrower.keys()):
#             node = Node(nd)
#             node.level = self.level
#             if not narrower[nd] and nd not in list_of_all_children:
#                 nodes[nd] = node
#                 self.children.append(node)
#             else:
#                 stack.append((nd, narrower[nd]))

#         # Process stack of nodes which are not fully defined. Use the defined
#         # nodes to add the children level by level.
#         while stack:
#             to_add = []
#             for nd, v in stack:
#                 all_children_defined = True
#                 for c in v:
#                     if c not in nodes:
#                         all_children_defined = False
#                 if all_children_defined:
#                     to_add.append((nd, v))

#             for nd, v in to_add:
#                 node = Node(nd)
#                 node.level = self.get_level(narrower, nd, self.level)
#                 for c in v:
#                     chnode = nodes[c]
#                     node.children.append(chnode)
#                 if nd not in list_of_all_children:  # "root" level
#                     node.level = self.level
#                     self.children.append(node)
#                 nodes[nd] = node
#                 stack.remove((nd, v))

#     def get_level(self, narrower, key, level=0):
#         """Return the depth level of a given node."""
#         for n, ch in narrower.items():
#             if key in ch:
#                 return self.get_level(narrower, n, level + 1)
#         return level

#     def as_dict(self):
#         """Return tree of nodes as nested dictionary."""
#         if self.children:
#             return {
#                 self.text: [
#                     node.as_dict()
#                     for node in sorted(self.children, key=lambda child: child.text)
#                 ]
#             }
#         return self.text

#     def as_indented_text(self, sep=" ", out=None):
#         """Return tree of nodes as indented text."""
#         if out is None:
#             out = []
#         for text, level in self.as_level_dict().items():
#             out.append(f"{level*sep}{text}")
#         return out

#     def as_level_dict(self, out=None):
#         """Return hierarchically sorted list of of all nodes in tree with level."""
#         if out is None:
#             out = {}
#         if self.children:
#             out[self.text] = self.level
#             for node in sorted(self.children, key=lambda t: t.text):
#                 node.as_level_dict(out)
#             return out
#         out[self.text] = self.level
#         return out

#     def as_narrower_dict(self, out=None):
#         """Return tree of nodes as flat dictionary of nodes with children."""
#         if out is None:
#             out = {}
#         if self.children:
#             out[self.text] = sorted([c.text for c in self.children])
#             for node in self.children:
#                 node.as_narrower_dict(out)
#         else:
#             out[self.text] = []
#         return out

#     def __eq__(self, other):
#         return (self.text, self.level, self.children) == (
#             other.text,
#             other.level,
#             other.children,
#         )

#     def __lt__(self, other):
#         return (self.text, self.level, self.children) < (
#             other.text,
#             other.level,
#             other.children,
#         )


# === Factory functions to build a tree of nodes ===


# def build_tree(text, sep=" "):
#     """Build tree of nodes from indented text."""
#     root = Node("root", sep=sep)
#     root.add_children([Node(line) for line in text.splitlines() if line.strip()])
#     return root


# def build_from_narrower(narrower):
#     """Build tree of nodes from narrower dictionary."""
#     roots = []
#     for k in narrower.keys():
#         # find which node(s) are not linked by any other
#         if k not in chain.from_iterable(list(narrower.values())):
#             roots.append(k)
#     if not roots:
#         raise ValueError("No root found on root level.")
#     if len(roots) == 1:
#         root = Node(roots[0])
#         narrower_no_root = copy(narrower)
#         narrower_no_root.pop(roots[0])
#     else:
#         root = Node("root")
#         narrower_no_root = copy(narrower)

#     root.add_nodes_narrower(narrower_no_root)
#     return root


# === NetworkX implementation ===============================================

def _get_edges(text_with_level, base_level):  # noqa: WPS231
    edges = []
    level_parent_map = {}
    for concept, level in text_with_level:
        if level not in level_parent_map:  # no parent stored for this level
            level_parent_map[level] = concept
        if level == max(level_parent_map):  # a new possible parent
            level_parent_map[level] = concept
            if level > base_level:
                edges.append((level_parent_map[level - 1], concept))
        elif level < max(level_parent_map):  # back to lower level
            # remove higher-level parents and register new parent for this level
            level_parent_map = {lvl: cpt for lvl, cpt in level_parent_map.items() if lvl <= level}
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
        text_with_level.append((concept, level))

    _, base_level = min(text_with_level, key=itemgetter(1))

    # Check if first line is at base level.
    if text_with_level:
        concept, level = text_with_level[0]
        if base_level != level:
            raise ValueError(f'First line "{concept}" must be at lowest level.')

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

# def _print_indented(sl, root_node, level=0, sep="  "):
#     successors = sl.pop(root_node)
#     print(level * sep + root_node)
#     for sn in successors:
#         if sn in sl:
#             _print_indented(sl, sn, level=level + 1, sep=sep)
#         else:
#             print((level + 1) * sep + sn)


# def dag_to_indent(termgraph, sep="  "):
#     subgraphs = [
#         termgraph.subgraph(c).copy()
#         for c in nx.connected_components(termgraph.to_undirected())
#     ]
#     for subgraph in subgraphs:
#         print(f"\nsubgraph: {subgraph}")
#         broken_edges = []
#         for cycle in nx.simple_cycles(subgraph):
#             edge = _break_cycles(subgraph, cycle)
#             if edge:
#                 broken_edges.append(edge)

#         # We need a clean subgraph without cylces for creating an indented tree.
#         subgraph_clean = subgraph.copy()
#         subgraph_clean.remove_edges_from(broken_edges)
#         roots = [node for node, degree in subgraph_clean.in_degree() if degree == 0]

#         for root in roots:
#             # successors in breadth-first-search
#             succ_bfs = dict(nx.bfs_successors(subgraph_clean, root))
#             _print_indented(succ_bfs, root, level=0)

#         # Add broken_edges
#         for edge in broken_edges:
#             start_node, end_node = edge
#             print(start_node)
#             print(sep + end_node)


def _break_cycles(dag, edges_cycle):
    # print(f"-> has cycle: {edges_cycle} - len={len(edges_cycle)}")
    if len(edges_cycle) < 3:
        print(f"-> Small unbreakable cycle! {edges_cycle}")
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
    """Build tree represenation of directed graph breaking cycles as needed."""
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
            edges.append((concept, child))
    dag = nx.DiGraph()
    dag.add_nodes_from(nodes)
    dag.add_edges_from(edges)
    return dag


def dag_to_narrower(dag):
    """Build children representation form networkx directed graph."""
    narrower = {}
    for node in dag.nodes:
        narrower[node] = list(dag.successors(node))
    return narrower


if __name__ == "__main__":
    # Show roundtrip: indented text -> dag -> indented text
    text = """
ex_1
    ex_2
    ex_3
        ex_4
        ex_5
    ex_6
        ex_7
ex_9
    ex_7
ex_4
    ex_1
ex_8
ex_10
    ex_11
"""
    print(f"Input: {text}")
    termdag = dag_from_indented_text(text, sep="    ")
    print("New indented output:")
    dag_to_indented_text(termdag)
    print("Children representation:")
    print(dag_to_narrower_dict(termdag))
