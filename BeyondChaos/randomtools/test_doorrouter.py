# Run this file as a module from the parent directory, i.e.:
#       python -m randomtools.test_doorrouter
from .doorrouter import Graph, DoorRouterException
from string import ascii_lowercase, ascii_uppercase
from sys import exc_info
from time import time
from subprocess import call
from collections import defaultdict
import random
import traceback

def get_graph(labels=None):
    if labels is None:
        labels = ascii_lowercase
    g = Graph(testing=True)
    for c in labels:
        g.Node(c, g)
    root = g.Node('root', g)
    assert g.testing
    g.set_root(root)
    assert g.reduce
    return g

def load_test_data(filename, root_label='1d1-001', unconnected=None):
    try:
        node_labels = set()
        edge_labels = set()
        requirements = defaultdict(set)
        with open(filename) as f:
            for line in f:
                line = line.strip()
                if line.startswith('.require '):
                    _, node, requirement = line.split(' ')
                    requirements[node].add(requirement)
                    continue
                edge, condition = line.split(': ')
                condition = condition.strip('*')
                assert condition[0] == '['
                assert condition[-1] == ']'
                source, destination = edge.split('->')
                condition = condition[1:-1]
                if condition:
                    labels = frozenset(condition.split(', '))
                    node_labels |= set(labels)
                    labels = '&'.join(labels)
                else:
                    labels = None
                node_labels.add(source)
                node_labels.add(destination)
                edge_labels.add((source, destination, labels))
        node_labels = sorted(node_labels)
        edge_labels = sorted(edge_labels,
                key=lambda e: (e[0], e[1], e[2] if e[2] is not None else ''))
        random.shuffle(node_labels)
        random.shuffle(edge_labels)
        g = Graph(testing=True)
        for n in node_labels:
            n = n.rstrip('?')
            if g.by_label(n) is not None:
                continue
            n = g.Node(n.rstrip('?'), g)
        for node, nodereqs in requirements.items():
            node = g.by_label(node)
            if node is None:
                continue
            for r in nodereqs:
                r = g.by_label(r)
                node.add_required(r)
        for source, destination, condition in edge_labels:
            if destination.endswith('?'):
                destination = destination.rstrip('?')
                questionable = True
            else:
                questionable = False
            g.add_edge(source, destination, condition=condition,
                       questionable=questionable)
        if unconnected is not None:
            g.unconnected = set()
            with open(unconnected) as f:
                for line in f:
                    n = g.by_label(line.strip())
                    if n is None:
                        n = g.Node(line.strip(), g)
                    g.unconnected.add(n)
            g.initial_unconnected = frozenset(g.unconnected)
        root = g.by_label('root')
        if root is not None:
            g.set_root(root)
        else:
            g.set_root(g.by_label(root_label))
        g.testing = False
    except AssertionError:
        raise Exception('Failure to load test data.')
    return g

def get_random_graph():
    g = get_graph(ascii_lowercase + ascii_uppercase)
    nodes = sorted(g.nodes)
    for n1 in nodes:
        for n2 in nodes:
            if n1 is n2:
                continue
            odds = int(round(len(nodes) ** 0.85))
            while True:
                if random.randint(0, odds) != 0:
                    break
                condition_length = random.randint(0, len(nodes))
                condition = random.sample(nodes, condition_length)
                g.add_edge(n1, n2, condition=frozenset(condition))
    g.rooted
    return g

class Replay:
    def __init__(self, filename, root='root'):
        self.progress_index = -1
        self.progression = {}
        with open(filename) as f:
            for line in f:
                if '#' in line:
                    line = line.split('#')[0]
                line = line.strip()
                if not line:
                    continue
                if line.count(' ') >= 2:
                    index, command, parameter = line.split(' ', 2)
                else:
                    index, command = line.split(' ')
                    parameter = None
                index = int(index)
                self.progression[index] = (command, parameter)

        self.graph = Graph(testing=True)
        for _, parameter in self.progression.values():
            if parameter is None:
                continue
            edge, _ = parameter.split(':')
            a, b = edge.split('->')
            _, cs = parameter.split('[')
            assert cs.endswith(']')
            cs = cs[:-1]
            if cs:
                cs = cs.split(', ')
            else:
                cs = []
            for n in [a, b] + cs:
                self.add_node(n)
        root = self.graph.by_label(root)
        self.graph.set_root(root)
        self.graph.testing = False
        self.graph.reduce = True
        self.needs_commit = True
        self.optimize_commits = False
        self.generative_phase = False

    def add_node(self, label):
        if label.endswith('?'):
            label = label.rstrip('?')
        n = self.graph.by_label(label)
        if n is None:
            n = self.graph.Node(label, parent=self.graph)
        self.needs_commit = True
        return n

    def parameter_to_nodes(self, parameter):
        questionable = False
        edge, _ = parameter.split(':')
        a, b = edge.split('->')
        if b.endswith('?'):
            b = b.rstrip('?')
            questionable = True
        _, cs = parameter.split('[')
        assert cs.endswith(']')
        cs = cs[:-1]
        cs = cs.split(', ')
        anode = self.graph.by_label(a)
        bnode = self.graph.by_label(b)
        return anode, bnode, cs, questionable

    def add_edge(self, parameter):
        anode, bnode, cs, questionable = self.parameter_to_nodes(parameter)
        count1 = len([e for e in anode.edges if e.destination is bnode])
        self.graph.add_edge(anode, bnode, condition='&'.join(cs),
                            procedural=self.generative_phase,
                            simplify=not self.generative_phase,
                            questionable=questionable)
        count2 = len([e for e in anode.edges if e.destination is bnode])
        if self.generative_phase:
            assert count2 == count1 + 1
        self.needs_commit = True

    def remove_edge(self, parameter):
        anode, bnode, cs, questionable = self.parameter_to_nodes(parameter)
        edges = [e for e in anode.edges
                 if e.destination is bnode and str(e).startswith(parameter)
                 and e.questionable == questionable]
        if self.generative_phase:
            old_edges = list(edges)
            edges = [e for e in edges if e.generated]
        assert edges
        for e in edges:
            e.remove()
        self.needs_commit = True

    def commit(self, ignore_commits=False):
        self.generative_phase = True
        if not self.needs_commit:
            return
        self.graph.clear_rooted_cache()
        if not ignore_commits:
            self.graph.rooted
        self.graph.commit()
        if self.optimize_commits:
            self.needs_commit = False

    def rollback(self):
        if not self.needs_commit:
            return
        self.graph.rollback()
        if self.optimize_commits:
            self.needs_commit = False

    def advance(self, ignore_commits=False):
        self.progress_index += 1
        if self.progress_index not in self.progression:
            return
        command, parameter = self.progression[self.progress_index]
        assert command in ('ADD', 'REMOVE', 'COMMIT', 'ROLLBACK')
        if command == 'ADD':
            self.add_edge(parameter)
        elif command == 'REMOVE':
            self.remove_edge(parameter)
        elif command == 'COMMIT':
            self.commit(ignore_commits=ignore_commits)
        elif command == 'ROLLBACK':
            self.rollback()

    def advance_to(self, index, ignore_commits=False):
        while self.progress_index < index:
            self.advance(ignore_commits=ignore_commits)

def pretty_guarantees(g):
    s = ''
    def fg_sort_key(fg):
        return '\n'.join(sorted(str(g) for g in fg))

    for n in sorted(g.reachable_from_root, key=lambda x: x.label):
        guaranteed = ' '.join(sorted(str(g) for g in n.guaranteed))
        s += f'{n.label}: {guaranteed}\n'
        for fg in sorted(n.full_guaranteed, key=fg_sort_key):
            guaranteed = ' '.join(sorted(str(g) for g in fg))
            s += f'  {guaranteed}\n'
    return s.strip()

def pretty_nodeset(ns):
    return ','.join(sorted(str(n) for n in ns))

def test_test():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('root', 'c', condition='b', directed=False)
    assert len(g.reachable_from_root) == 4
    assert g.reachable_from_root == g.root_reachable_from

def test_double_one_way1():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'c', condition='a|b')
    assert g.by_label('c') not in g.reachable_from_root

def test_double_one_way2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'root', condition='b')
    g.add_edge('root', 'b')
    g.add_edge('b', 'root', condition='a')
    g.add_edge('root', 'c', condition='a|b')
    assert g.by_label('c') not in g.reachable_from_root

def test_double_one_way3():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b', condition='a', directed=False)
    g.add_edge('root', 'c', condition='a&b')
    assert g.by_label('c') in g.reachable_from_root

def test_uncertain_one_way1():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b')
    g.add_edge('b', 'root', condition='a')
    g.add_edge('root', 'c', condition='a&b', directed=False)
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('b') not in g.root_reachable_from
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') in g.root_reachable_from

def test_uncertain_one_way2():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b')
    g.add_edge('b', 'root', condition='a')
    g.add_edge('b', 'c', condition='a&b', directed=False)
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('b') not in g.root_reachable_from
    # This may be inconsistent, but being able to detect this case
    # is probably unnecessary.
    #assert g.by_label('c') in g.root_reachable_from

def test_uncertain_one_way3():
    g = get_graph()
    g.add_edge('root', 'b')
    g.add_edge('b', 'a', directed=False)
    g.add_edge('b', 'root', condition='a')
    g.add_edge('root', 'c', condition='a&b', directed=False)
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('b') in g.root_reachable_from
    assert g.by_label('c') in g.root_reachable_from

def test_uncertain_one_way4():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b')
    g.add_edge('b', 'root', condition='c')
    g.add_edge('root', 'c', condition='a&b', directed=False)
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('b') not in g.root_reachable_from
    assert g.by_label('c') not in g.root_reachable_from

def test_uncertain_one_way5():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b')
    g.add_edge('b', 'root', condition='a')
    g.add_edge('b', 'c', condition='a&b', directed=False)
    g.add_edge('c', 'root', condition='a')
    assert g.by_label('b') in g.reachable_from_root or \
            g.by_label('c') in g.reachable_from_root
    assert g.by_label('b') not in g.root_reachable_from
    assert g.by_label('c') in g.root_reachable_from

def test_uncertain_one_way6():
    g = get_graph()
    g.reduce = False
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'd')
    g.add_edge('c', 'f')
    g.add_edge('d', 'f')
    g.add_edge('f', 'g', condition='a|b')
    g.add_edge('g', 'h')
    g.add_edge('h', 'i', condition='c|d')
    g.add_edge('i', 'root')
    assert g.reachable_from_root == g.root_reachable_from

def test_uncertain_one_way7():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b')
    g.add_edge('b', 'root', condition='a')
    g.add_edge('b', 'a')
    g.add_edge('b', 'c', condition='a&b', directed=False)
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('b') in g.root_reachable_from
    assert g.by_label('c') in g.root_reachable_from
    assert g.reachable_from_root == g.root_reachable_from

def test_uncertain_one_way8():
    g = get_graph()
    g.add_edge('root', 'b')
    g.add_edge('b', 'a')
    g.add_edge('a', 'root')
    g.add_edge('b', 'c', condition='a')
    g.add_edge('c', 'b', condition='a&b')
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('b') in g.root_reachable_from
    assert g.by_label('c') in g.root_reachable_from
    assert g.reachable_from_root == g.root_reachable_from

def test_uncertain_condition1():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b', directed=True)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('c', 'root', condition='a', directed=True)
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('b') in g.get_no_return_nodes(allow_nodes=g.nodes)
    assert g.reduce is True
    rfb, brf, _ = g.by_label('b').get_guaranteed_reachable(and_from=True)
    assert g.by_label('c') not in rfb
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    assert g.by_label('a') in g.by_label('c').guaranteed
    assert g.by_label('b') in rfc
    assert g.by_label('b') not in crf
    assert g.by_label('c') in g.root_reachable_from
    assert g.by_label('b') not in g.root_reachable_from

def test_uncertain_condition2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'c')
    g.add_edge('a', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') not in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') not in drf
    assert g.by_label('root') in drf

def test_uncertain_condition3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'c')
    g.add_edge('root', 'd')
    g.add_edge('a', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') not in rfc
    assert g.by_label('d') not in crf
    assert g.by_label('c') not in rfd
    assert g.by_label('c') not in drf

def test_multiple_conditions1():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)
    g.rooted

    assert g.by_label('d').full_guaranteed == g.by_label('c').full_guaranteed

    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('d') in g.reachable_from_root
    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_conditions2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('root', 'x')
    g.add_edge('x', 'c')
    g.add_edge('c', 'd', condition='x', directed=True)
    g.rooted

    assert g.by_label('d').full_guaranteed == g.by_label('c').full_guaranteed

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') not in crf
    assert g.by_label('root') in crf
    assert g.by_label('c') not in rfd
    assert g.by_label('c') in drf

def test_multiple_conditions3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('root', 'x')
    g.add_edge('x', 'c')
    g.add_edge('d', 'c', condition='x', directed=True)
    g.rooted

    assert g.by_label('d').full_guaranteed < g.by_label('c').full_guaranteed

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') not in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') not in drf
    assert g.by_label('root') in drf

def test_multiple_conditions4():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('c', 'd', condition='x', directed=False)
    g.rooted

    assert g.by_label('d').full_guaranteed == g.by_label('c').full_guaranteed

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_conditions5():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('c', 'd', condition='x', directed=True)
    g.rooted

    assert g.by_label('d').full_guaranteed == g.by_label('c').full_guaranteed

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_conditions6():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('d', 'c', condition='x', directed=True)
    g.rooted

    assert g.by_label('d').full_guaranteed == g.by_label('c').full_guaranteed

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_conditions7():
    g = get_graph()
    g.add_edge('root', 'w')
    g.add_edge('root', 'x')
    g.add_edge('w', 'y')
    g.add_edge('x', 'y')
    g.add_edge('y', 'z', condition='w', directed=False)
    g.add_edge('y', 'z', condition='x', directed=False)

    g.add_edge('y', 'z', condition='i', directed=True)
    g.rooted

    assert g.by_label('z').full_guaranteed == g.by_label('y').full_guaranteed

    assert g.reduce is True
    rfy, yrf, _ = g.by_label('y').get_guaranteed_reachable(and_from=True)
    rfz, zrf, _ = g.by_label('z').get_guaranteed_reachable(and_from=True)
    assert g.by_label('z') in rfy
    assert g.by_label('z') in yrf
    assert g.by_label('y') in rfz
    assert g.by_label('y') in zrf

def test_multiple_conditions_triangle01():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.rooted
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') not in g.root_reachable_from

def test_multiple_conditions_triangle02():
    g = get_graph()
    g.add_edge('root', 'b')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.rooted
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') not in g.root_reachable_from

def test_multiple_conditions_triangle03():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.rooted
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') not in g.root_reachable_from

def test_multiple_conditions_triangle04():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.rooted
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') in g.root_reachable_from

def test_multiple_conditions_triangle05():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('a', 'd')
    g.add_edge('b', 'd')
    g.add_edge('c', 'e', condition='a')
    g.add_edge('d', 'e', condition='b')
    g.rooted
    assert g.by_label('e') in g.reachable_from_root

def test_multiple_conditions_triangle06():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'e', condition='a')
    g.add_edge('c', 'e', condition='b')
    g.rooted
    assert g.by_label('e') in g.reachable_from_root

def test_multiple_conditions_triangle07():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'e', condition='a&b')
    g.rooted
    assert g.by_label('e') in g.reachable_from_root

def test_multiple_conditions_triangle08():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'c')
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'e', condition='a&b')
    g.rooted
    assert g.by_label('e') in g.reachable_from_root

def test_multiple_conditions_triangle09():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'c')
    g.add_edge('a', 'c', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('a', 'e', condition='b&c')
    g.add_edge('b', 'e', condition='a&c')
    g.add_edge('c', 'e', condition='a&b')
    g.rooted
    assert g.by_label('e') in g.reachable_from_root

def test_multiple_conditions_triangle10():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'c')
    g.add_edge('a', 'c', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('a', 'e', condition='b')
    g.add_edge('a', 'e', condition='c')
    g.add_edge('b', 'e', condition='a')
    g.add_edge('b', 'e', condition='c')
    g.add_edge('c', 'e', condition='a')
    g.add_edge('c', 'e', condition='b')
    g.rooted
    assert g.by_label('e') in g.reachable_from_root

def test_multiple_conditions_triangle11():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.add_edge('a', 'root', condition='c')
    g.rooted
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') in g.root_reachable_from

def test_multiple_conditions_triangle12():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('a', 'root', condition='a&b')
    g.rooted
    assert g.by_label('a') in g.reachable_from_root
    assert g.by_label('a') in g.root_reachable_from
    assert g.by_label('b') in g.reachable_from_root
    assert g.by_label('b') in g.root_reachable_from

def test_multiple_conditions_triangle13():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'x', condition='c')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.add_edge('a', 'x', condition='c')
    g.rooted
    assert g.by_label('c') in g.reachable_from_root

def test_multiple_conditions_triangle14():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_edge('a', 'c', condition='b', directed=False)
    g.add_edge('a', 'x', condition='c')
    g.add_edge('x', 'root', condition='c')
    g.rooted
    assert g.by_label('c') in g.reachable_from_root
    assert g.by_label('c') in g.root_reachable_from

def test_multiple_uncertain_conditions1():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('c', 'd', condition='x', directed=True)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_uncertain_conditions2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('d', 'c', condition='x', directed=True)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_uncertain_conditions3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('c', 'd', condition='x', directed=False)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') in drf

def test_multiple_uncertain_conditions4():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'c')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('c', 'd', condition='x', directed=False)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') not in rfc
    assert g.by_label('d') in crf
    assert g.by_label('c') in rfd
    assert g.by_label('c') not in drf
    assert g.by_label('root') in drf

def test_multiple_uncertain_conditions5():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'c')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'c')
    g.add_edge('c', 'd', condition='a', directed=False)
    g.add_edge('c', 'd', condition='b', directed=False)

    g.add_edge('c', 'd', condition='x', directed=True)
    g.rooted

    assert frozenset({}) not in g.by_label('d').full_guaranteed
    assert frozenset({g.by_label(l) for l in ('a', 'x')}) in \
            g.by_label('d').full_guaranteed
    assert frozenset({g.by_label('x')}) in \
            g.by_label('d').full_guaranteed

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') not in rfc
    assert g.by_label('d') not in crf
    assert g.by_label('c') not in rfd
    assert g.by_label('c') not in drf

def test_multiple_uncertain_conditions6():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a', directed=True)
    g.add_edge('c', 'd', condition='b', directed=True)

    g.add_edge('c', 'd', condition='x', directed=False)
    g.rooted

    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    rfd, drf, _ = g.by_label('d').get_guaranteed_reachable(and_from=True)
    assert g.by_label('d') in rfc
    assert g.by_label('d') not in crf
    assert g.by_label('c') not in rfd
    assert g.by_label('c') in drf

def test_distant_condition():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('c', 'b', condition='x')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root', condition='x')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf

def test_distant_uncertain_condition1():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', condition='y', directed=False)
    g.add_edge('c', 'b', condition='x')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root', condition='x')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf

def test_distant_uncertain_condition2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('c', 'b', condition='x')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root', condition='x&y')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf

def test_distant_uncertain_condition3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', condition='y', directed=False)
    g.add_edge('c', 'b', condition='x&y')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root', condition='x')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf
    assert g.by_label('c') in rfr
    assert g.by_label('c') not in rrf

def test_distant_uncertain_condition4():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', condition='y', directed=False)
    g.add_edge('c', 'b', condition='x')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root', condition='x&y')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf
    assert g.by_label('c') in rfr
    assert g.by_label('c') not in rrf

def test_distant_uncertain_condition5():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('c', 'b', condition='y')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') not in rrf
    assert g.by_label('c') in rfr
    assert g.by_label('c') not in rrf

def test_distant_uncertain_condition6():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'c', condition='y')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('c', 'b', condition='y')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf
    assert g.by_label('c') in rfr
    assert g.by_label('c') in rrf

def test_distant_uncertain_condition7():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'y', directed=False)
    g.add_edge('b', 'z', condition='y', directed=False)
    g.add_edge('b', 'c', condition='y')
    g.add_edge('c', 'x', condition='z', directed=False)
    g.add_edge('c', 'b', condition='x')
    g.add_edge('b', 'a', condition='x')
    g.add_edge('a', 'root', condition='x&y&z')
    g.rooted

    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('x') in rfr
    assert g.by_label('x') in rrf
    assert g.by_label('c') in rfr
    assert g.by_label('c') not in rrf

def test_backtracking1():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b', directed=False)
    assert len(g.root.edges) == 2
    g.add_edge('a', 'c', directed=False)
    g.add_edge('b', 'd', condition='c', directed=False)
    g.add_edge('c', 'e', condition='d', directed=False)
    g.add_edge('d', 'f', condition='e', directed=False)
    assert len(g.root.edges) == 2
    g.rooted
    assert g.reduce is True
    g.reduce = False
    assert len(g.root.edges) == 2
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('a') in rfr
    assert g.by_label('b') in rfr
    assert g.by_label('f') in rfr
    assert g.by_label('f') in rrf
    assert len(rfr) == len({'root', 'a', 'b', 'c', 'd', 'e', 'f'})
    assert rrf == rfr

def test_backtracking2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('a', 'd')
    g.add_edge('b', 'c')
    g.add_edge('b', 'g')
    g.add_edge('c', 'h')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('d', 'e')
    g.add_edge('d', 'i', directed=False)
    g.add_edge('e', 'f')
    g.add_edge('f', 'd')
    g.add_edge('f', 'y', condition='x')
    g.add_edge('g', 'j', directed=False)
    g.add_edge('h', 'b')
    g.add_edge('h', 'k')
    g.add_edge('j', 'i')
    g.add_edge('k', 'e')

    g.reduce = False
    g.clear_rooted_cache()
    g.rooted

    # PATH:
    # root > a > b > c > x! > c > h > b > g > j > i > d > e > f > y
    assert g.by_label('y') in g.reachable_from_root
    assert g.by_label('k') not in g.by_label('x').guaranteed
    assert g.by_label('k') not in g.by_label('f').guaranteed
    assert g.by_label('k') not in g.by_label('y').guaranteed

def test_circular_dependency():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('root', 'c')
    g.add_edge('root', 'x')
    g.add_edge('root', 'y')
    g.add_edge('root', 'z')
    g.add_edge('a', 'b', condition='y&z', directed=False)
    g.add_edge('b', 'c', condition='x&z', directed=False)
    g.add_edge('c', 'a', condition='x&y', directed=False)
    g.add_edge('a', 'x', condition='b', directed=False)
    g.add_edge('b', 'y', condition='c', directed=False)
    g.add_edge('c', 'z', condition='a', directed=False)
    g.rooted
    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert len(rfr) == 7
    assert len(rrf) == 1

def test_no_add_root1():
    g = Graph(testing=True)
    root = g.Node('1d1-001', g)
    g.set_root(root)
    try:
        a = g.Node('049-001', g)
        b = g.Node('0b5-00c', g)
    except NotImplementedError:
        return
    g.add_edge(a, b)
    g.add_edge(a, b)
    assert False

def test_no_add_root2():
    g = Graph(testing=True)
    root = g.Node('1d1-001', g)
    a = g.Node('049-001', g)
    b = g.Node('0b5-00c', g)
    g.set_root(root)
    g.add_edge(a, b)
    g.add_edge(a, b)

def test_loop1():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=True)
    g.add_edge('b', 'c', directed=True)
    g.add_edge('c', 'a', directed=True)
    g.add_edge('b', 'x', directed=False)
    g.add_edge('c', 'y', condition='x', directed=True)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.reduce is False
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.reduced_graph is None
    assert g.by_label('y') in rfn

def test_graph_reduction01():
    g = get_graph()
    g.add_edge('root', 'b', directed=False)
    g.add_edge('root', 'c', directed=True)
    g.add_edge('c', 'root', condition='b', directed=True)
    g.rooted
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True, do_reduce=False)
    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    assert g.root not in rfc
    assert g.root in crf
    assert g.by_label('c') in rfr
    assert g.by_label('c') not in rrf

def test_graph_reduction02():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'b', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('a', 'c', directed=True)
    g.add_edge('c', 'root', condition='b', directed=True)
    g.clear_rooted_cache()
    g.reduced_graph = g.get_reduced_graph()
    g.rooted
    assert g.reduce is True
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    assert g.root not in rfc
    assert g.root in crf
    assert g.by_label('c') in rfr
    assert g.by_label('c') not in rrf

def test_graph_reduction03():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('c', 'd', directed=True)
    g.add_edge('d', 'e', condition='b', directed=False)
    g.clear_rooted_cache()
    g.reduced_graph = g.get_reduced_graph()
    g.rooted
    assert g.reduced_graph.by_label('b') in \
            g.reduced_graph.conditional_nodes
    assert g.by_label('b') in g.by_label('d').guaranteed
    assert g.reduced_graph.by_label('b') in \
            g.reduced_graph.by_label('d').guaranteed

def test_graph_reduction04():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('a', 'c', directed=False)
    g.add_edge('c', 'd', directed=True)
    g.add_edge('d', 'e', condition='b', directed=False)
    g.clear_rooted_cache()
    g.reduced_graph = g.get_reduced_graph()
    g.rooted
    assert g.reduced_graph.by_label('b') in \
            g.reduced_graph.conditional_nodes
    assert g.by_label('b') not in g.by_label('d').guaranteed
    assert g.reduced_graph.by_label('b') not in \
            g.reduced_graph.by_label('d').guaranteed

def test_graph_reduction05():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('root', 'z', directed=True)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('z', 'y', directed=False)
    g.add_edge('y', 'b', directed=True)
    g.add_edge('b', 'y', condition='q', directed=False)

    g.clear_rooted_cache()
    g.reduced_graph = g.get_reduced_graph()
    g.rooted
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True, do_reduce=False)
    assert g.reduce is True
    rfx, xrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    rfn2, n2rf, _ = g.by_label('a').get_guaranteed_reachable(
            and_from=True, do_reduce=False)
    assert g.reduce is True
    rfx2, x2rf, _ = g.by_label('a').get_guaranteed_reachable(and_from=True)
    assert rfn == rfx
    assert nrf == xrf
    assert rfn2 == rfx2
    assert n2rf == x2rf

def test_graph_reduction06():
    g = get_graph()
    g.add_edge('root', 'h', directed=False)
    g.add_edge('h', 'g', directed=False)
    g.add_edge('g', 'i', directed=False)
    g.add_edge('i', 'j', directed=False)
    g.add_edge('j', 'f', directed=False)
    g.add_edge('f', 'e', directed=False)
    g.add_edge('e', 'd', directed=False)
    g.add_edge('d', 'b', directed=True)
    g.add_edge('d', 'c', directed=True)
    g.add_edge('b', 'c', directed=True)
    g.add_edge('c', 'd', condition='z', directed=True)
    g.add_edge('b', 'a', directed=False)
    g.add_edge('c', 's', directed=False)
    g.add_edge('s', 't', condition='k&m&q&s&v&x', directed=False)
    g.add_edge('t', 'u', condition='k&m&q&s&v&x', directed=False)
    g.add_edge('t', 'w', directed=False)
    g.add_edge('w', 'v', directed=False)
    g.add_edge('s', 'u', directed=False)
    g.add_edge('m', 'u', directed=False)
    g.add_edge('m', 'n', directed=False)
    g.add_edge('n', 'q', directed=False)
    g.add_edge('q', 'r', directed=True)
    g.add_edge('r', 'q', condition='z', directed=True)
    g.add_edge('r', 'x', directed=False)
    g.add_edge('x', 'y', directed=False)
    g.add_edge('y', 'k', directed=False)
    g.add_edge('k', 'l', directed=False)
    g.add_edge('l', 'o', directed=False)
    g.add_edge('o', 'p', directed=False)
    g.add_edge('p', 'v', directed=False)

    g.clear_rooted_cache()
    g.reduced_graph = g.get_reduced_graph()
    g.rooted
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True, do_reduce=False)
    assert g.reduce is True
    rfx, xrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    rfn2, n2rf, _ = g.by_label('b').get_guaranteed_reachable(
            and_from=True, do_reduce=False)
    assert g.reduce is True
    rfx2, x2rf, _ = g.by_label('b').get_guaranteed_reachable(and_from=True)
    assert rfn == rfx
    assert nrf == xrf
    assert rfn2 == rfx2
    assert n2rf == x2rf

def test_graph_reduction07():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=True)
    g.add_edge('c', 'b', condition='a', directed=True)

    g.clear_rooted_cache()
    g.rooted
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True, do_reduce=False)
    assert g.reduce is True
    rfx, xrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert rfn == rfx
    assert nrf == xrf

def test_graph_reduction08():
    g = get_graph()
    g.reduce = False
    g.Requirement.from_line('.guarantee c b', g)
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('a', 'c', directed=False)
    g.clear_rooted_cache()
    g.rooted
    assert g.reduced_graph is None
    assert g.by_label('b') not in g.by_label('c').guaranteed

def test_graph_reduction09():
    g = get_graph()
    g.reduce = True
    g.Requirement.from_line('.guarantee c b', g)
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('a', 'c', directed=False)
    g.clear_rooted_cache()
    g.rooted
    assert g.reduced_graph
    assert g.by_label('b') not in g.by_label('c').guaranteed

def test_graph_reduction10():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('a', 'c', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('b', 'd', directed=False)
    g.rooted
    assert g.reduced_graph
    assert g.by_label('a') in g.by_label('d').guaranteed
    assert g.by_label('b') in g.by_label('d').guaranteed
    assert g.by_label('c') not in g.by_label('d').guaranteed

def test_graph_reduction11():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b', directed=True)
    g.add_edge('b', 'c', directed=True)
    g.add_edge('c', 'a', directed=True)
    g.add_edge('b', 'x', directed=False)
    g.add_edge('c', 'y', condition='x', directed=True)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.reduce is False
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.reduced_graph is None
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.reduced_graph
    assert g.reduce is True
    rfx, xrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('y') in rfn
    assert g.by_label('y') in rfx
    assert rfn == rfx
    assert nrf == xrf

def test_graph_reduction12():
    g = get_graph()
    g.add_edge('root', 'b', directed=False)
    g.add_edge('c', 'root', condition='b', directed=False)
    g.rooted
    rfr, rrf, _ = g.root.get_guaranteed_reachable(and_from=True, do_reduce=False)
    assert g.reduce is True
    rfc, crf, _ = g.by_label('c').get_guaranteed_reachable(and_from=True)
    assert g.root in rfc
    assert g.root in crf
    assert g.by_label('c') in rfr
    assert g.by_label('c') in rrf

def test_graph_reduction13():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('d', 'e', directed=False)
    g.add_edge('e', 'f', directed=False)
    g.add_edge('b', 'd', directed=True)
    g.add_edge('e', 'h', directed=True)
    g.add_edge('g', 'b', directed=True)
    g.add_edge('h', 'i', directed=True)
    g.add_edge('a', 'z', condition='f', directed=True)
    g.add_edge('d', 'g', condition='root&c', directed=True)
    g.add_edge('x', 'y', condition='z', directed=True)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.reduce is False
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.reduced_graph is None
    assert g.by_label('z') in rfn
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.reduced_graph
    assert g.reduce is True
    rfx, xrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('z') in rfx
    assert rfn == rfx
    assert nrf == xrf

def test_guarantees1():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=True)
    g.add_edge('a', 'c', directed=True)
    g.add_edge('b', 'd', directed=True)
    g.add_edge('c', 'e', directed=True)
    g.add_edge('d', 'f', directed=True)
    g.add_edge('e', 'g', directed=True)
    g.add_edge('f', 'h', directed=True)
    g.add_edge('h', 'i', directed=True)
    g.add_edge('g', 'j', directed=True)
    g.add_edge('g', 'k', condition='x', directed=True)
    g.add_edge('i', 'l', directed=True)
    g.add_edge('j', 'k', directed=True)
    g.add_edge('l', 'm', directed=True)
    g.add_edge('m', 'x', directed=True)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('j') in g.by_label('k').guaranteed

def test_guarantees2():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=True)
    g.add_edge('a', 'c', directed=True)
    g.add_edge('b', 'd', directed=True)
    g.add_edge('c', 'e', directed=True)
    g.add_edge('d', 'f', directed=True)
    g.add_edge('e', 'g', directed=True)
    g.add_edge('f', 'h', directed=True)
    g.add_edge('h', 'i', directed=True)
    g.add_edge('g', 'j', directed=True)
    g.add_edge('g', 'k', condition='x', directed=True)
    g.add_edge('i', 'l', directed=True)
    g.add_edge('j', 'k', directed=True)
    g.add_edge('l', 'm', directed=True)
    g.add_edge('m', 'x', directed=True)
    g.add_edge('x', 'g', condition='y', directed=True)
    g.add_edge('root', 'y', directed=False)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('x') in g.rooted
    assert g.by_label('g') in g.rooted
    assert g.by_label('k') in g.rooted
    assert g.by_label('j') not in g.by_label('k').guaranteed

def test_guarantees3():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=True)
    g.add_edge('a', 'c', directed=True)
    g.add_edge('b', 'd', directed=True)
    g.add_edge('c', 'e', directed=True)
    g.add_edge('d', 'f', directed=True)
    g.add_edge('e', 'g', directed=True)
    g.add_edge('f', 'h', directed=True)
    g.add_edge('h', 'i', directed=True)
    g.add_edge('g', 'j', directed=True)
    g.add_edge('g', 'k', condition='x', directed=True)
    g.add_edge('i', 'l', directed=True)
    #g.add_edge('j', 'k', directed=True)
    g.add_edge('l', 'm', directed=True)
    g.add_edge('m', 'x', directed=True)
    g.add_edge('x', 'g', condition='y', directed=True)
    g.add_edge('root', 'y', directed=False)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('x') in g.rooted
    assert g.by_label('g') in g.rooted
    assert g.by_label('k') in g.rooted
    assert g.by_label('j') not in g.by_label('k').guaranteed

def test_graph_reduction_guarantees1():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('b', 'd', directed=True)
    g.add_edge('c', 'e', directed=True)
    g.add_edge('d', 'f', directed=False)
    g.add_edge('e', 'g', directed=False)
    g.add_edge('f', 'h', directed=False)
    g.add_edge('f', 'i', directed=True)
    g.add_edge('g', 'j', directed=True)
    g.add_edge('i', 'k', directed=True)
    g.add_edge('j', 'l', directed=False)
    g.add_edge('k', 'm', directed=True)
    g.add_edge('l', 'n', directed=True)
    g.add_edge('m', 'o', directed=True)
    g.add_edge('n', 'p', directed=True)
    g.add_edge('n', 'q', condition='x', directed=True)
    g.add_edge('o', 'r', directed=True)
    g.add_edge('p', 's', directed=True)
    g.add_edge('q', 's', directed=False)
    g.add_edge('r', 't', directed=True)
    g.add_edge('t', 'x', directed=True)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.reduce is False
    rfn, nrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.by_label('p') in g.by_label('s').guaranteed
    guarantees = {n: n.guaranteed for n in rfn}
    assert g.reduced_graph is None
    g.reduce = True
    g.clear_rooted_cache()
    g.clear_node_guarantees()
    g.rooted
    assert g.reduced_graph
    assert g.reduce is True
    rfx, xrf, _ = g.root.get_guaranteed_reachable(and_from=True)
    assert g.reduced_graph.node_mapping[g.by_label('p')] in \
            g.reduced_graph.node_mapping[g.by_label('s')].guaranteed
    assert g.by_label('p') in g.by_label('s').guaranteed
    for n in sorted(rfx):
        assert n.guaranteed >= guarantees[n]
    assert rfn == rfx
    assert nrf == xrf

def test_graph_reductionx():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('a', 'z', condition='h', directed=True)
    g.add_edge('b', 'c', directed=True)
    g.add_edge('b', 'd', directed=False)
    g.add_edge('c', 'e', directed=False)
    g.add_edge('c', 'f', condition='root&j', directed=True)
    g.add_edge('d', 'g', directed=False)
    g.add_edge('e', 'h', directed=False)
    g.add_edge('e', 'i', directed=True)
    g.add_edge('f', 'd', directed=True)
    g.add_edge('g', 'b', directed=False)
    g.add_edge('g', 'j', directed=False)
    g.add_edge('i', 'k', directed=True)
    g.add_edge('x', 'y', condition='z', directed=True)
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted

def test_graph_reduction_guaranteed1():
    g = get_graph()
    g.add_edge('root', 'a', directed=True)
    g.add_edge('a', 'b', directed=True)
    g.add_edge('b', 'c', directed=True)
    g.add_edge('c', 'e', directed=True)
    g.add_edge('d', 'f', directed=True)
    g.add_edge('e', 'g', directed=True)
    g.add_edge('g', 'c', directed=True)

    g.add_edge('b', 'd', directed=False)
    g.add_edge('f', 'h', directed=False)
    g.add_edge('g', 'i', directed=False)
    g.add_edge('h', 'j', directed=False)
    g.add_edge('h', 'k', directed=False)
    g.add_edge('x', 'y', directed=False)

    g.add_edge('e', 'x', condition='a&i&j&k', directed=True)
    g.add_edge('f', 'd', condition='a&j&k', directed=True)

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    edges1 = '\n'.join([e for e in sorted(str(e) for e in g.all_edges)])
    guaranteed1 = pretty_guarantees(g)

    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    for n in g.nodes:
        if n.full_guaranteed is not None:
            n.simplify_full_guaranteed()
    edges2 = '\n'.join([e for e in sorted(str(e) for e in g.all_edges)])
    guaranteed2 = pretty_guarantees(g)

    assert edges1 == edges2
    assert guaranteed1 == guaranteed2

def test_graph_reduction_guaranteed2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'p')
    g.add_edge('p', 'q')

    g.add_edge('a', 'x')
    g.add_edge('x', 'y', condition='x')
    g.add_edge('y', 'q')
    g.add_edge('q', 'p', condition='y')

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('b') not in g.by_label('p').guaranteed

def test_graph_reduction_guaranteed3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('a', 'x')
    #g.add_edge('x', 'y', condition='x')
    g.add_edge('x', 'y', condition='p')
    g.add_edge('x', 'p', directed=False)
    g.add_edge('y', 'z')
    #g.add_edge('z', 'c', condition='z')
    g.add_edge('z', 'c', condition='q')
    g.add_edge('z', 'q', directed=False)
    g.add_edge('c', 'z')

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('b') not in g.by_label('x').guaranteed
    assert g.by_label('b') not in g.by_label('y').guaranteed
    assert g.by_label('b') not in g.by_label('z').guaranteed
    assert g.by_label('b') not in g.by_label('p').guaranteed
    assert g.by_label('b') not in g.by_label('q').guaranteed
    assert g.by_label('b') not in g.by_label('c').guaranteed

def test_graph_reduction_guaranteed4():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'a')
    g.add_edge('b', 'd')
    g.add_edge('d', 'e', directed=False)
    g.add_edge('d', 'x')
    g.add_edge('e', 'f', directed=False)
    g.add_edge('e', 'q', condition='y')
    #g.add_edge('x', 'p', condition='x')
    g.add_edge('x', 'p', condition='z')
    g.add_edge('x', 'z', directed=False)
    g.add_edge('p', 'f')
    g.add_edge('p', 'y', directed=False)

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted

    for n in g.reachable_from_root:
        if n.label in ('c', 'q'):
            continue
        assert g.by_label('c') not in n.guaranteed
    assert g.by_label('c') in g.by_label('c').guaranteed
    assert g.by_label('c') not in g.by_label('q').guaranteed

def test_graph_reduction_guaranteed5():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('a', 'd')
    g.add_edge('b', 'c')
    g.add_edge('b', 'g')
    g.add_edge('c', 'h')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('d', 'e')
    g.add_edge('d', 'i', directed=False)
    g.add_edge('e', 'f')
    g.add_edge('f', 'd')
    g.add_edge('f', 'y', condition='x')
    g.add_edge('g', 'j', directed=False)
    g.add_edge('h', 'b')
    g.add_edge('h', 'k')
    g.add_edge('j', 'i')
    g.add_edge('k', 'e')

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted

    # PATH:
    # root > a > b > c > x! > c > h > b > g > j > i > d > e > f > y
    assert g.by_label('k') not in g.by_label('x').guaranteed
    assert g.by_label('k') not in g.by_label('f').guaranteed
    assert g.by_label('k') not in g.by_label('y').guaranteed

def test_graph_reduction_guaranteed6():
    g1 = get_graph()
    g1.add_edge('root', 'a', directed=False)
    g1.add_edge('x', 'y', condition='a')
    g1.reduce = False
    guaranteed1 = pretty_guarantees(g1)
    assert frozenset({g1.by_label('a')}) in g1.root.full_guaranteed

    g2 = get_graph()
    g2.add_edge('root', 'a', directed=False)
    g2.add_edge('x', 'y', condition='a')
    g2.reduce = True
    guaranteed2 = pretty_guarantees(g2)
    assert frozenset({g2.by_label('a')}) in g2.root.full_guaranteed
    assert guaranteed1 == guaranteed2

def test_orphanable1():
    g = get_graph()
    g.add_edge('root', 'x')
    edges = g.add_edge('x', 'y')
    g.clear_rooted_cache()
    g.rooted
    assert len(edges) == 1
    edge = edges.pop()
    assert edge.get_guaranteed_orphanable() == {g.by_label('y')}

def test_orphanable2():
    g = get_graph()
    g.add_edge('root', 'x')
    edges = g.add_edge('x', 'y')
    g.add_edge('x', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd')
    g.add_edge('d', 'y')
    g.clear_rooted_cache()
    g.rooted
    assert len(edges) == 1
    edge = edges.pop()
    assert edge.get_guaranteed_orphanable() == set()

def test_orphanable3():
    g = get_graph()
    g.add_edge('root', 'x', directed=False)
    g.add_multiedge('x=>y')
    g.add_edge('y', 'x')
    g.add_edge('x', 'a', directed=False)
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('c', 'd', directed=False)
    g.add_edge('y', 'z', directed=False)
    g.add_edge('d', 'y', condition='z', directed=False)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    g.verify()

def test_orphanable4():
    g = get_graph()
    g.add_edge('root', 'x')
    g.add_multiedge('x=>y')
    g.add_edge('x', 'a')
    g.add_edge('a', 'b')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd')
    g.add_edge('d', 'y')
    g.clear_rooted_cache()
    g.rooted
    try:
        g.verify()
        assert False
    except DoorRouterException:
        pass

def test_orphanable5():
    g = get_graph()
    g.add_edge('root', 'x', directed=False)
    g.add_multiedge('x=>y')
    g.add_edge('x', 'a')
    g.add_edge('a', 'y')
    try:
        g.verify()
        assert False
    except DoorRouterException:
        pass

def test_orphanable6():
    g = get_graph()
    g.add_edge('root', 'x', directed=False)
    g.add_multiedge('x=>y')
    g.add_edge('x', 'a')
    g.add_edge('a', 'y')
    g.add_edge('y', 'x')
    try:
        g.verify()
        assert False
    except DoorRouterException:
        pass

def test_orphanable7():
    g = get_graph()
    g.reduce = False
    g.add_edge('root', 'a', directed=False)
    g.add_edge('root', 'x', directed=False)
    g.add_edge('root', 'x', condition='a')
    g.add_edge('root', 'b', condition='x')
    g.rooted
    edge = {e for e in g.all_edges if 'root->x' in str(e)
            and not e.true_condition}.pop()
    assert edge not in g.by_label('b').guaranteed_edges
    assert not edge.get_guaranteed_orphanable()

def test_orphanable_backtracking1():
    g = get_graph()
    g.add_edge('root', 'y')
    g.add_edge('y', 'x', directed=False)
    g.add_edge('y', 'a', condition='x')
    g.rooted
    assert len(g.by_label('x').reverse_edges) == 1
    e = list(g.by_label('x').reverse_edges)[0]
    assert g.by_label('x') in g.by_label('a').guaranteed
    assert e in g.by_label('x').guaranteed_edges
    assert e in g.by_label('a').guaranteed_edges
    assert g.by_label('a') in e.get_guaranteed_orphanable()
    assert e.pair in g.by_label('a').guaranteed_edges
    assert g.by_label('a') in e.pair.get_guaranteed_orphanable()

def test_orphanable_backtracking2():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'z', condition='q', directed=False)
    g.add_edge('a', 'q')
    g.add_edge('q', 'x')
    g.add_edge('x', 'a', condition='y')
    g.add_edge('x', 'y', directed=False)
    g.reduce = False
    g.rooted
    assert frozenset({g.by_label(n) for n in {'q', 'y'}}) \
            in g.by_label('a').full_guaranteed
    assert frozenset({g.by_label(n) for n in {'q', 'y'}}) \
            in g.by_label('z').full_guaranteed
    assert frozenset({g.by_label(n) for n in {'q'}}) \
            not in g.by_label('z').full_guaranteed
    assert g.reachable_from_root == g.root_reachable_from
    assert g.by_label('z') in g.reachable_from_root
    assert g.by_label('y') in g.by_label('z').guaranteed

def test_orphanable_reduction1():
    g1 = get_graph()
    g1.add_edge('root', 'y')
    g1.add_edge('y', 'z', condition='x')
    g1.add_edge('x', 'y', directed=False)
    g1.reduce = True
    g1.clear_rooted_cache()
    g1.rooted
    e1 = [e for e in g1.all_edges if 'x->y' in str(e)]
    assert len(e1) == 1
    e1 = e1[0]

    g2 = get_graph()
    g2.add_edge('root', 'y')
    g2.add_edge('y', 'z', condition='x')
    g2.add_edge('x', 'y', directed=False)
    g2.reduce = False
    g2.clear_rooted_cache()
    g2.rooted
    e2 = [e for e in g2.all_edges if 'x->y' in str(e)]
    assert len(e2) == 1
    e2 = e2[0]

    orphans1 = e1.get_guaranteed_orphanable()
    orphans2 = e2.get_guaranteed_orphanable()
    assert g1.by_label('z') in orphans1
    assert g2.by_label('z') in orphans2
    assert len(orphans1) == len(orphans2)
    assert pretty_nodeset(orphans1) == pretty_nodeset(orphans2)

def test_orphanable_reduction2():
    g1 = get_graph()
    g1.test_break = False
    g1.add_edge('root', 'y')
    g1.add_edge('y', 'w', condition='z')
    g1.add_edge('x', 'y', directed=False)
    g1.add_edge('x', 'z', directed=False)
    g1.reduce = True
    g1.clear_rooted_cache()
    g1.rooted
    e1 = [e for e in g1.all_edges if 'x->y' in str(e)]
    assert len(e1) == 1
    e1 = e1[0]
    orphans1 = e1.get_guaranteed_orphanable()
    assert g1.by_label('w') in orphans1

    g2 = get_graph()
    g2.add_edge('root', 'y')
    g2.add_edge('y', 'w', condition='z')
    g2.add_edge('x', 'y', directed=False)
    g2.add_edge('x', 'z', directed=False)
    g2.reduce = False
    g2.clear_rooted_cache()
    g2.rooted
    e2 = [e for e in g2.all_edges if 'x->y' in str(e)]
    assert len(e2) == 1
    e2 = e2[0]

    orphans2 = e2.get_guaranteed_orphanable()
    assert g2.by_label('w') in orphans2
    assert len(orphans1) == len(orphans2)
    assert pretty_nodeset(orphans1) == pretty_nodeset(orphans2)

def test_orphanable_reduction3():
    g1 = get_graph()
    g1.add_edge('root', 'a')
    g1.add_edge('a', 'b')
    g1.add_edge('b', 'c')
    g1.add_edge('b', 'w', condition='z')
    g1.add_edge('c', 'd')
    g1.add_edge('d', 'a')
    g1.add_edge('d', 'e')
    g1.add_edge('e', 'c')
    g1.add_edge('e', 'y', directed=False)
    g1.add_edge('x', 'y', directed=False)
    g1.add_edge('x', 'z', directed=False)
    g1.reduce = True
    g1.clear_rooted_cache()
    g1.rooted
    e1 = [e for e in g1.all_edges if 'x->y' in str(e)]
    assert len(e1) == 1
    e1 = e1[0]

    g2 = get_graph()
    g2.add_edge('root', 'a')
    g2.add_edge('a', 'b')
    g2.add_edge('b', 'c')
    g2.add_edge('b', 'w', condition='z')
    g2.add_edge('c', 'd')
    g2.add_edge('d', 'a')
    g2.add_edge('d', 'e')
    g2.add_edge('e', 'c')
    g2.add_edge('e', 'y', directed=False)
    g2.add_edge('x', 'y', directed=False)
    g2.add_edge('x', 'z', directed=False)
    g2.reduce = False
    g2.clear_rooted_cache()
    g2.rooted
    e2 = [e for e in g2.all_edges if 'x->y' in str(e)]
    assert len(e2) == 1
    e2 = e2[0]

    orphans1 = e1.get_guaranteed_orphanable()
    orphans2 = e2.get_guaranteed_orphanable()
    assert pretty_nodeset(orphans1) == pretty_nodeset(orphans2)

def test_orphanable_reduction4():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'y')
    g.add_edge('y', 'b', condition='a', directed=False)
    g.add_edge('y', 'x', directed=False)
    g.add_edge('y', 'z', condition='b')
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    e1 = [e for e in g.all_edges if 'x->y' in str(e)]
    assert len(e1) == 1
    e1 = e1[0]
    assert g.by_label('z') not in e1.get_guaranteed_orphanable()

def test_rerank1():
    g = get_graph()
    g.add_edge('root', 'x', directed=False)
    g.add_edge('root', 'a', condition='x')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.reduced_graph is not None
    assert g.by_label('c') in g.reachable_from_root
    assert 'a->b' in str(g._edge_reachable_from_root)
    assert g.by_label('c') not in g.by_label('b').guaranteed

def test_smart_reachable_from1():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a|b')
    g.add_edge('d', 'root')
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('a') not in g.by_label('c').guaranteed
    assert g.by_label('b') not in g.by_label('c').guaranteed
    assert g.by_label('c').full_guaranteed == {
            frozenset({g.by_label('a')}),
            frozenset({g.by_label('b')}),
            frozenset({g.by_label('a'), g.by_label('b')}),
            }
    assert g.by_label('c') in g.root_reachable_from
    assert g.root_reachable_from == g.reachable_from_root

def test_smart_reachable_from2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a')
    g.add_edge('c', 'e', condition='b')
    g.add_edge('d', 'root')
    g.add_edge('e', 'root')
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('a') not in g.by_label('c').guaranteed
    assert g.by_label('b') not in g.by_label('c').guaranteed
    assert g.by_label('c').full_guaranteed == {
            frozenset({g.by_label('a')}),
            frozenset({g.by_label('b')}),
            frozenset({g.by_label('a'), g.by_label('b')}),
            }
    assert g.by_label('d') in g.root_reachable_from
    assert g.by_label('e') in g.root_reachable_from
    assert g.by_label('c') in g.root_reachable_from
    assert g.root_reachable_from == g.reachable_from_root

def test_smart_reachable_from3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a')
    g.add_edge('c', 'e', condition='b')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('d', 'root')
    g.add_edge('e', 'root')
    g.reduce = True
    g.add_edge('root', 'c')
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('x') not in g.root_reachable_from
    assert g.by_label('a') not in g.by_label('c').guaranteed
    assert g.by_label('b') not in g.by_label('c').guaranteed
    assert g.by_label('c').full_guaranteed == {
            frozenset({g.by_label('a'), g.by_label('b')}),
            frozenset({}),
            }
    assert g.by_label('d') in g.root_reachable_from
    assert g.by_label('e') in g.root_reachable_from
    assert g.by_label('c') not in g.root_reachable_from
    assert g.root_reachable_from != g.reachable_from_root

def test_smart_reachable_from4():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'd', condition='a')
    g.add_edge('c', 'e', condition='b')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('d', 'root')
    g.add_edge('e', 'root')
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('c') in g.root_reachable_from
    assert g.by_label('x') in g.root_reachable_from
    g.commit()
    g.add_edge('root', 'c')
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('c') not in g.root_reachable_from
    assert g.by_label('x') not in g.root_reachable_from
    assert g.by_label('a') not in g.by_label('c').guaranteed
    assert g.by_label('b') not in g.by_label('c').guaranteed
    assert g.by_label('c').full_guaranteed == {
            frozenset({g.by_label('a'), g.by_label('b')}),
            frozenset({}),
            }
    assert g.by_label('d') in g.root_reachable_from
    assert g.by_label('e') in g.root_reachable_from
    assert g.by_label('c') not in g.root_reachable_from
    assert g.root_reachable_from != g.reachable_from_root

def test_reachable_from_not_reachable1():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('b', 'a', directed=True)
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('b') in g.root_reachable_from
    assert g.by_label('b') not in g.reachable_from_root
    assert g.by_label('a') in g.reachable_from_root
    assert g.by_label('a') in g.root_reachable_from

def test_reachable_from_not_reachable2():
    g = get_graph()
    g.add_edge('root', 'a', directed=False)
    g.add_edge('a', 'b')
    g.add_edge('b', 'q', directed=False)
    g.add_edge('b', 'x')
    g.add_edge('x', 'a', condition='q')
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('q') in g.root_reachable_from
    assert g.reachable_from_root == g.root_reachable_from | {g.by_label('x')}

def test_reachable_from_not_reachable3():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'root', condition='b')
    g.add_edge('b', 'a', condition='c', directed=False)
    g.add_edge('c', 'b')
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('root') in g.reachable_from_root
    assert g.by_label('a') in g.reachable_from_root
    assert g.by_label('b') not in g.reachable_from_root
    assert g.by_label('c') not in g.reachable_from_root
    assert g.by_label('root') in g.root_reachable_from
    assert g.by_label('a') not in g.root_reachable_from
    assert g.by_label('b') not in g.root_reachable_from
    assert g.by_label('c') in g.root_reachable_from

def test_no_return1():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('a', 'u')
    g.add_edge('a', 'y', condition='x')
    g.add_edge('a', 'b', condition='y', directed=False)
    g.add_edge('y', 'root')
    g.unconnected = {g.by_label('u')}
    g.clear_rooted_cache()
    g.rooted
    assert g.by_label('a') not in g.root_reachable_from
    # This is technically inaccurate but harmless?
    #assert g.by_label('b') in g.root_reachable_from
    assert g.by_label('u') not in g.root_reachable_from
    assert g.by_label('x') in g.root_reachable_from
    assert g.by_label('y') in g.root_reachable_from
    g.get_no_return_nodes(allow_nodes=g.get_add_edge_options())

def test_reduced_edges1():
    g = get_graph()
    g.add_edge('root', 'a', condition='x')
    g.add_edge('root', 'a', condition='y')
    g.add_edge('root', 'a', condition='x&y')
    g.get_reduced_graph()

def test_reduced_edges2():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'x', directed=False)
    g.add_edge('x', 'y', directed=False)
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    x = g.by_label('x')
    y = g.by_label('y')
    e = [e1 for e1 in y.reverse_edges if 'x->y' in str(e1)]
    assert len(e) == 1
    assert y.reverse_edges == set(e)
    e = e.pop()
    assert e.source.rooted
    assert e.destination.rooted
    assert e in g.root.edge_guar_to[y]

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    e = [e1 for e1 in y.reverse_edges if 'x->y' in str(e1)]
    assert len(e) == 1
    assert y.reverse_edges == set(e)
    e = e.pop()
    assert e.source.rooted
    assert e.destination.rooted
    assert e in g.root.edge_guar_to[y]

def test_rerank2():
    VERIFICATION = {
        'root': 1,
        'a': 2,
        'b': 3, 'f': 3,
        'c': 4, 'v': 4, 'z': 4,
        'q': 5, 'd': 5, 'w': 5, 'x': 5,
        'e': 6,
        'y': 6,
    }
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('c', 'q', directed=False)
    g.add_edge('c', 'd')
    g.add_edge('d', 'e')
    g.add_edge('e', 'w')
    g.add_edge('w', 'y', condition='q')
    g.add_edge('a', 'f')
    g.add_edge('f', 'v')
    g.add_edge('f', 'z')
    g.add_edge('z', 'x')

    g.reduce = True
    g.clear_rooted_cache()
    g.rooted
    g.commit()
    g.add_edge('v', 'w', directed=False)
    g.clear_rooted_cache()
    g.rooted

    ranks1 = {(n.label, n.rank) for n in g.rooted}
    assert len(g.rooted) == len(VERIFICATION)
    assert g.by_label('d') not in g.by_label('y').guaranteed
    assert g.by_label('e') not in g.by_label('y').guaranteed
    for n in g.rooted:
        assert VERIFICATION[n.label] == n.rank

    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('a', 'b', directed=False)
    g.add_edge('b', 'c', directed=False)
    g.add_edge('c', 'q', directed=False)
    g.add_edge('c', 'd')
    g.add_edge('d', 'e')
    g.add_edge('e', 'w')
    g.add_edge('w', 'y', condition='q')
    g.add_edge('a', 'f')
    g.add_edge('f', 'v')
    g.add_edge('f', 'z')
    g.add_edge('z', 'x')

    g.reduce = True
    g.add_edge('v', 'w', directed=False)
    g.clear_rooted_cache()
    g.rooted

    ranks2 = {(n.label, n.rank) for n in g.rooted}
    assert g.by_label('d') not in g.by_label('y').guaranteed
    assert g.by_label('e') not in g.by_label('y').guaranteed
    assert len(g.rooted) == len(VERIFICATION)
    for n in g.rooted:
        assert VERIFICATION[n.label] == n.rank

    assert ranks1 == ranks2

def test_rerank3():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('root', 'q')
    g.add_edge('a', 'b')
    g.add_edge('a', 'p', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'root')
    g.add_edge('q', 'x', condition='p')
    g.add_edge('a', 'root', condition='q')
    g.add_edge('y', 'c')

    g.add_edge('x', 'y')
    g.clear_rooted_cache()
    ranks1 = {(n.label, n.rank) for n in g.rooted}

    assert g.by_label('x').guaranteed == (g.by_label('q').guaranteed |
                                          g.by_label('p').guaranteed |
                                          {g.by_label('x')})
    assert g.by_label('y').guaranteed == (g.by_label('x').guaranteed |
                                          {g.by_label('y')})

    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('root', 'q')
    g.add_edge('a', 'b')
    g.add_edge('a', 'p', directed=False)
    g.add_edge('b', 'c')
    g.add_edge('c', 'root')
    g.add_edge('q', 'x', condition='p')
    g.add_edge('a', 'root', condition='q')
    g.add_edge('y', 'c')

    g.rooted
    g.commit()
    assert g.by_label('x').guaranteed == (g.by_label('q').guaranteed |
                                          g.by_label('p').guaranteed |
                                          g.by_label('c').guaranteed |
                                          {g.by_label('x')})

    g.add_edge('x', 'y')
    g.clear_rooted_cache()
    ranks2 = {(n.label, n.rank) for n in g.rooted}

    assert g.by_label('x').guaranteed == (g.by_label('q').guaranteed |
                                          g.by_label('p').guaranteed |
                                          {g.by_label('x')})
    assert g.by_label('y').guaranteed == (g.by_label('x').guaranteed |
                                          {g.by_label('y')})

    assert ranks1 == ranks2

def test_rerank4():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('root', 'b', condition='x', directed=False)
    g.add_edge('c', 'x', directed=False)
    g.clear_rooted_cache()
    g.rooted
    g.commit()
    g.add_edge('p', 'q')
    g.clear_rooted_cache()
    g.rooted
    g.commit()
    g.add_edge('b', 'x', directed=False)
    g.clear_rooted_cache()
    g.rooted
    ranks1 = {(n.label, n.rank) for n in g.rooted}

    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('a', 'b')
    g.add_edge('root', 'b', condition='x', directed=False)
    g.add_edge('c', 'x', directed=False)
    g.clear_rooted_cache()
    g.rooted
    #g.commit()
    g.add_edge('p', 'q')
    g.clear_rooted_cache()
    g.rooted
    #g.commit()
    g.add_edge('b', 'x', directed=False)
    g.clear_rooted_cache()
    g.rooted
    ranks2 = {(n.label, n.rank) for n in g.rooted}

    assert ranks1 == ranks2

def test_rerank5():
    g1 = get_graph()
    g1.reduce = True
    g1.add_edge('root', 'x')
    g1.add_edge('x', 'a')
    g1.add_edge('a', 'b')
    g1.add_edge('b', 'root')
    g1.add_edge('root', 'y', condition='x', directed=False)
    g1.add_edge('x', 'z', condition='y')
    g1.clear_rooted_cache()
    g1.rooted
    #g1.commit()
    g1.add_edge('x', 'root')
    g1.clear_rooted_cache()
    g1.rooted
    ranks1 = {(n.label, n.rank) for n in g1.rooted}

    g2 = get_graph()
    g2.reduce = True
    g2.add_edge('root', 'x')
    g2.add_edge('x', 'a')
    g2.add_edge('a', 'b')
    g2.add_edge('b', 'root')
    g2.add_edge('root', 'y', condition='x', directed=False)
    g2.add_edge('x', 'z', condition='y')
    g2.clear_rooted_cache()
    g2.rooted
    g2.commit()
    g2.add_edge('x', 'root')
    g2.clear_rooted_cache()
    g2.rooted
    ranks2 = {(n.label, n.rank) for n in g2.rooted}

    assert g2.by_label('a') not in g2.by_label('z').guaranteed
    assert g2.by_label('b') not in g2.by_label('z').guaranteed
    assert ranks1 == ranks2

def test_rerank6():
    g1 = get_graph()
    g1.reduce = True
    g1.add_edge('root', 'x')
    g1.add_edge('x', 'a')
    g1.add_edge('a', 'b')
    g1.add_edge('b', 'root')
    g1.add_edge('root', 'y', condition='x')
    g1.add_edge('y', 'root')
    g1.add_edge('root', 'z', condition='y')
    g1.clear_rooted_cache()
    g1.rooted
    #g1.commit()
    g1.add_edge('x', 'root')
    g1.clear_rooted_cache()
    g1.rooted
    ranks1 = {(n.label, n.rank) for n in g1.rooted}

    g2 = get_graph()
    g2.reduce = True
    g2.add_edge('root', 'x')
    g2.add_edge('x', 'a')
    g2.add_edge('a', 'b')
    g2.add_edge('b', 'root')
    g2.add_edge('root', 'y', condition='x')
    g2.add_edge('y', 'root')
    g2.add_edge('root', 'z', condition='y')
    g2.clear_rooted_cache()
    g2.rooted
    g2.commit()
    g2.add_edge('x', 'root')
    g2.clear_rooted_cache()
    g2.rooted
    ranks2 = {(n.label, n.rank) for n in g2.rooted}

    assert g2.by_label('a') not in g2.by_label('z').guaranteed
    assert g2.by_label('b') not in g2.by_label('z').guaranteed
    assert ranks1 == ranks2

def test_rerank7():
    g1 = get_graph(ascii_lowercase + ascii_uppercase)
    g1.reduce = True
    g1.add_edge('root', 'a')
    g1.add_edge('a', 'b')
    g1.add_edge('b', 'c')
    g1.add_edge('c', 'x')
    g1.add_edge('x', 'd', condition='x')
    g1.add_edge('x', 'e', condition='x')
    g1.add_edge('d', 'root')
    g1.add_edge('e', 'q')
    g1.add_edge('q', 'x')
    g1.add_edge('q', 'f', condition='x')
    g1.add_edge('root', 'q')
    g1.clear_rooted_cache()
    g1.rooted

    g2 = get_graph(ascii_lowercase + ascii_uppercase)
    g2.reduce = True
    g2.add_edge('root', 'a')
    g2.add_edge('a', 'b')
    g2.add_edge('b', 'c')
    g2.add_edge('c', 'x')
    g2.add_edge('x', 'd', condition='x')
    g2.add_edge('x', 'e', condition='x')
    g2.add_edge('d', 'root')
    g2.add_edge('e', 'q')
    g2.add_edge('q', 'x')
    g2.add_edge('q', 'f', condition='x')
    g2.clear_rooted_cache()
    g2.rooted
    g2.commit()
    g2.test_break = True
    g2.add_edge('root', 'q')
    g2.clear_rooted_cache()
    g2.rooted

    expected_ranks = [
        ('root', 1),
        ('q', 2),
        ('x', 3),
        ('f', 4),
        ]
    assert g1.by_label('a') not in g1.by_label('f').guaranteed
    assert g2.by_label('a') not in g2.by_label('f').guaranteed
    ranks1 = {(n.label, n.rank) for n in g1.rooted}
    ranks2 = {(n.label, n.rank) for n in g2.rooted}
    for label, rank in expected_ranks:
        assert g1.by_label(label).rank == rank
        assert g2.by_label(label).rank == rank
    assert ranks1 == ranks2

def test_edge_rank1():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('root', 'x', directed=False)
    g.add_edge('root', 'b', condition='x')
    g.add_edge('a', 'b')
    g.rooted
    b = g.by_label('b')
    e = [e1 for e1 in g.all_edges if 'root->b' in str(e1)][0]
    assert g.by_label('x').rank > g.by_label('root').rank
    assert g.by_label('x').rank == g.by_label('a').rank
    assert e.rank == g.by_label('x').rank
    assert b.rank > g.by_label('a').rank
    assert b.rank > g.by_label('x').rank

def test_required_nodes1():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'x')
    g.add_edge('root', 'y')
    g.add_edge('x', 'z')
    g.add_edge('y', 'z')
    g.add_edge('z', 'root')
    g.Requirement.from_line('.require x z', g)
    g.Requirement.from_line('.require y z', g)
    try:
        g.rooted
    except DoorRouterException:
        return
    assert False

def test_required_nodes2():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('root', 'b', condition='a')
    g.add_edge('a', 'x')
    g.add_edge('x', 'y')
    g.add_edge('a', 'b', condition='y')
    g.add_edge('b', 'y')
    g.add_edge('y', 'root')
    g.Requirement.from_line('.require x y', g)
    try:
        g.rooted
    except DoorRouterException:
        return
    assert False

def test_avoid_reachable1():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('a', 'q', directed=False)
    g.add_edge('a', 'b', condition='q')
    g.rooted
    b = g.by_label('b')
    assert b in g.rooted
    assert b in g.root.get_naive_avoid_reachable()

def test_avoid_reachable2():
    g = get_graph()
    g.reduce = True
    g.add_edge('root', 'a')
    g.add_edge('a', 'p', directed=False)
    g.add_edge('a', 'q', directed=False)
    g.add_edge('a', 'x', condition='p')
    g.add_edge('x', 'y')
    g.add_edge('x', 'z', condition='q')
    g.add_edge('y', 'b')
    g.rooted

    edge = sorted(g.by_label('y').reverse_edges)[0]
    assert edge.source.label == 'x'
    orphans1 = edge.get_guaranteed_orphanable()
    orphans2 = g.reachable_from_root - \
            g.root.get_naive_avoid_reachable(avoid_edges={edge})
    assert orphans1 == orphans2

def test_one_time_edge():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b', directed=False)
    g.add_edge('b', 'c', condition='a', directed=False)
    g.add_multiedge('a>>b')
    g.clear_rooted_cache()
    g.rooted
    assert len(g.reachable_from_root) == 4
    assert g.by_label('a') not in g.root_reachable_from
    assert len(g.root_reachable_from) == 3
    g.verify()

def test_double_required():
    g = get_graph()
    g.add_edge('root', 'a')
    g.add_edge('root', 'b')
    g.add_edge('a', 'c')
    g.add_edge('b', 'c')
    g.add_edge('c', 'root')
    g.Requirement.from_line('.require a c', g)
    g.Requirement.from_line('.require b c', g)
    try:
        g.verify()
    except DoorRouterException as e:
        assert 'require c' in str(e)
        return
    g.rooted
    assert False

def test_custom_replay(filename='test_replay.txt',
                       midpoint=0, root='1d1-001'):
    try:
        slowrep = Replay(filename, root=root)
        slowrep.advance_to(midpoint, ignore_commits=True)
        checkpoints = {i for i in slowrep.progression
                       if i >= midpoint and 'COMMIT' in slowrep.progression[i]}
        checkpoints.add(midpoint)
    except:
        return
    for checkpoint in sorted(checkpoints):
        try:
            slowrep.advance_to(checkpoint, ignore_commits=False)
            fastrep = Replay(filename, root=root)
            fastrep.advance_to(checkpoint, ignore_commits=True)
            slowranks = {(n.label, n.rank) for n in slowrep.graph.rooted}
            fastranks = {(n.label, n.rank) for n in fastrep.graph.rooted}
            #if slowranks != fastranks:
            #    print(f'FAIL at line {checkpoint}: '
            #          f'{slowrep.progression[checkpoint]}')
        except:
            return
        assert slowranks == fastranks
        #print(f'Checkpoint {checkpoint} CLEARED')

def test_custom_replay_full(filename='test_replay.txt', midpoint=0):
    slowrep = Replay(filename, root='1d1-001')
    slowrep.advance_to(midpoint, ignore_commits=True)
    checkpoints = {i for i in slowrep.progression
                   if i >= midpoint and 'COMMIT' in slowrep.progression[i]}
    checkpoints.add(midpoint)
    for checkpoint in sorted(checkpoints):
        print('ROOTING SLOWREP')
        slowrep.advance_to(checkpoint, ignore_commits=False)
        print('ROOTING FASTREP')
        fastrep = Replay(filename, root='1d1-001')
        fastrep.advance_to(checkpoint, ignore_commits=True)
        slowranks = {(n.label, n.rank) for n in slowrep.graph.rooted}
        fastranks = {(n.label, n.rank) for n in fastrep.graph.rooted}
        if slowranks != fastranks:
            print(f'FAIL at line {checkpoint}: '
                  f'{slowrep.progression[checkpoint]}')
        assert slowranks == fastranks
        print(f'Checkpoint {checkpoint} CLEARED')

def test_custom(filename='test_edge_data.txt'):
    g = load_test_data(filename)
    g.reduce = True
    g.clear_rooted_cache()
    g.rooted

def test_custom_graph_reduction(filename='test_edge_data.txt'):
    try:
        g1 = load_test_data(filename)
        g1.reduce = True
        g1.clear_rooted_cache()
        g1.rooted

        g2 = load_test_data(filename)
        g2.reduce = False
        g2.clear_rooted_cache()
        g2.rooted

        edges1 = '\n'.join([e for e in sorted(str(e) for e in g1.all_edges)])
        edges2 = '\n'.join([e for e in sorted(str(e) for e in g2.all_edges)])
        assert edges1 == edges2

        guaranteed1 = pretty_guarantees(g1)
        guaranteed2 = pretty_guarantees(g2)
        #if guaranteed1 != guaranteed2:
        #    with open('_tgrg1.txt', 'w+') as f:
        #        f.write(guaranteed1)
        #    with open('_tgrg2.txt', 'w+') as f:
        #        f.write(guaranteed2)
    except:
        return
    assert guaranteed1 == guaranteed2

def test_custom_orphanable(filename='test_edge_data.txt'):
    g = load_test_data(filename)
    g.reduce = True
    g.reduce = False
    g.clear_rooted_cache()
    g.rooted
    edges = sorted(g.all_edges)
    for e in edges:
        if 'x->y' in str(e):
            orphans1 = e.get_guaranteed_orphanable()
            orphans2, _ = e.get_bridge_double_orphanable()
            assert orphans1 == orphans2

def test_custom_orphanable_reduction(filename='test_edge_data.txt'):
    try:
        g1 = load_test_data(filename)
        g1.reduce = True
        g1.clear_rooted_cache()
        g1.rooted
        e1 = [e for e in g1.all_edges if 'x->y' in str(e)]
        assert len(e1) == 1
        e1 = e1[0]

        g2 = load_test_data(filename)
        g2.reduce = False
        g2.clear_rooted_cache()
        g2.rooted
        e2 = [e for e in g2.all_edges if 'x->y' in str(e)]
        assert len(e2) == 1
        e2 = e2[0]

        orphans1 = e1.get_guaranteed_orphanable()
        orphans2 = e2.get_guaranteed_orphanable()
    except AssertionError:
        return
    try:
        assert pretty_nodeset(orphans1) == pretty_nodeset(orphans2)
    except DoorRouterException:
        return


if __name__ == '__main__':
    total = 0
    failed_tests = []
    for fname, f in sorted(globals().items()):
        if not isinstance(f, type(get_graph)):
            continue
        if fname.startswith('test_custom'):
            continue
        if not fname.startswith('test_'):
            continue
        if fname.startswith('test_random_'):
            num_trials = 10
        else:
            num_trials = 1
        for _ in range(num_trials):
            try:
                f()
                msg = f'. {fname}'
            except AssertionError:
                _, _, tb = exc_info()
                tb_info = traceback.extract_tb(tb)
                filename, line, func, text = tb_info[-1]
                error = f'{line}: {text}'[:40]
                msg = f'x {fname} - {error}'
                failed_tests.append((fname, error))
            except Exception:
                _, _, tb = exc_info()
                tb_info = traceback.extract_tb(tb)
                filename, line, func, text = tb_info[-1]
                error = f'{line}: {text}'[:40]
                msg = f'E {fname} - {error}'
                failed_tests.append((fname, error))
            total += 1
            print(msg)
    print(f'Failed {len(failed_tests)}/{total} tests:')
    for fname, error in failed_tests:
        print(' ', fname, error)
