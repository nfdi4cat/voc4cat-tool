# -*- coding: utf-8 -*-

from copy import copy
from functools import total_ordering
from itertools import chain
from warnings import warn


@total_ordering
class Node:
    """
    Node class to build a linked tree of nodes.

    The tree can be built from

    - indented text (the indent-seperator can be adjusted)
    - a dictionary with node-children key-value pairs
    """

    def __init__(self, indented_line, sep=" "):
        self.children = []
        split_line = indented_line.rstrip().split(sep)
        self.level = len(split_line) - 1
        self.text = split_line[self.level]
        if sep is not None and len(sep) > 1 and self.text.startswith(sep[0]):
            warn(f'Node "{self.text}": Incomplete separator "{sep}"?')

    def add_children(self, nodes):
        """Add more child nodes to node."""
        if not nodes:
            return
        for node in nodes:
            if self.level > node.level:
                raise ValueError(
                    f'Level of node "{node.text}" lower than of ' "root node."
                )
            if nodes[0].level > node.level:
                raise ValueError(
                    f'Level of node "{node.text}" lower than of ' "first node to add."
                )
        self.__add_children(nodes)

    def __add_children(self, nodes_in):
        # Make a copy to avoid changes to nodes_in.
        nodes = list(nodes_in)
        childlevel = nodes[0].level
        while nodes:
            node = nodes.pop(0)
            if node.level == childlevel:  # add node as a child
                self.children.append(node)
            elif (node.level - childlevel) == 1:  # grandchildren of last child
                nodes.insert(0, node)
                if self.children:
                    self.children[-1].__add_children(nodes)
            elif (node.level - childlevel) > 1:
                raise ValueError(
                    "Indentation inreases by more than one " f'level for "{node.text}"'
                )
            elif node.level <= self.level:  # sibling, no more children
                nodes.insert(0, node)
                return

    def add_nodes_narrower(self, narrower):
        """Add children and their level from narrower dict."""
        nodes = {}
        stack = []
        list_of_all_children = list(chain.from_iterable([v for v in narrower.values()]))

        # Check if all children are also key in narrower.
        for ch in list_of_all_children:
            if ch not in narrower.keys():
                raise ValueError(f'Child "{ch}" is not defined.')

        # Create nodes that are never present as child and store in nodes.
        # Only these nodes are fully defined at this point.
        for nd in list(narrower.keys()):
            node = Node(nd)
            node.level = self.level
            if not narrower[nd] and nd not in list_of_all_children:
                nodes[nd] = node
                self.children.append(node)
            else:
                stack.append((nd, narrower[nd]))

        # Process stack of nodes which are not fully defined. Use the defined
        # nodes to add the children level by level.
        while stack:
            to_add = []
            for nd, v in stack:
                all_children_defined = True
                for c in v:
                    if c not in nodes:
                        all_children_defined = False
                if all_children_defined:
                    to_add.append((nd, v))

            for nd, v in to_add:
                node = Node(nd)
                node.level = self.get_level(narrower, nd, self.level)
                for c in v:
                    chnode = nodes[c]
                    node.children.append(chnode)
                if nd not in list_of_all_children:  # "root" level
                    node.level = self.level
                    self.children.append(node)
                nodes[nd] = node
                stack.remove((nd, v))

    def get_level(self, narrower, key, level=0):
        """Return the depth level of a given node."""
        for n, ch in narrower.items():
            if key in ch:
                return self.get_level(narrower, n, level + 1)
        return level

    def as_dict(self):
        """Return tree of nodes as nested dictionary."""
        if len(self.children) > 0:
            return {
                self.text: [
                    node.as_dict()
                    for node in sorted(self.children, key=lambda child: child.text)
                ]
            }
        else:
            return self.text

    def as_indented_text(self, sep=" ", out=None):
        """Return tree of nodes as indented text."""
        if out is None:
            out = []
        for text, level in self.as_level_dict().items():
            out.append(f"{level*sep}{text}")
        return out

    def as_level_dict(self, out=None):
        """Return hierarchically sorted list of of all nodes in tree with level."""
        if out is None:
            out = {}
        if len(self.children) > 0:
            out[self.text] = self.level
            for node in sorted(self.children, key=lambda t: t.text):
                node.as_level_dict(out)
            return out
        else:
            out[self.text] = self.level
            return out

    def as_narrower_dict(self, out=None):
        """Return tree of nodes as flat dictionary of nodes with children."""
        if out is None:
            out = {}
        if len(self.children) > 0:
            out[self.text] = sorted([c.text for c in self.children])
            for node in self.children:
                node.as_narrower_dict(out)
        else:
            out[self.text] = []
        return out

    def __eq__(self, other):
        return (self.text, self.level, self.children) == (
            other.text,
            other.level,
            other.children,
        )

    def __lt__(self, other):
        return (self.text, self.level, self.children) < (
            other.text,
            other.level,
            other.children,
        )


# === Factory functions to build a tree of nodes ===


def build_tree(text, sep=" "):
    """Build tree of nodes from indented text."""
    root = Node("root", sep=sep)
    root.add_children([Node(line) for line in text.splitlines() if line.strip()])
    return root


def build_from_narrower(narrower):
    """Build tree of nodes from narrower dictionary."""
    roots = []
    for k in narrower.keys():
        # find which node(s) are not linked by any other
        if k not in chain.from_iterable([v for v in narrower.values()]):
            roots.append(k)
    if len(roots) == 1:
        root = Node(roots[0])
        narrower_no_root = copy(narrower)
        del narrower_no_root[roots[0]]
    elif len(roots) < 1:
        raise ValueError("No root found on root level.")
    else:
        root = Node("root")
        narrower_no_root = copy(narrower)

    root.add_nodes_narrower(narrower_no_root)
    return root
