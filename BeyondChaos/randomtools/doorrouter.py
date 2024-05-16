from .utils import cached_property, read_lines_nocomment, summarize_state, \
                    utilrandom as random
from collections import defaultdict
from copy import deepcopy
from functools import total_ordering
from hashlib import md5
from itertools import product
from os import listdir, path
from sys import stdout
from time import time, sleep
from .utils import fake_yaml as yaml


DEBUG = False
REDUCE = True
MODULE_FILEPATH, _ = path.split(__file__)
DEFAULT_CONFIG_FILENAME = path.join(MODULE_FILEPATH, 'default.doorrouter.yaml')


def log(line):
    if DEBUG:
        line = line.strip()
        print(line)
        stdout.flush()


class DoorRouterException(Exception):
    pass


class RollbackMixin:
    def commit(self, version=None):
        if not hasattr(self, '_rollback'):
            self._rollback = {}
        for attr in self.ROLLBACK_ATTRIBUTES:
            if not hasattr(self, attr):
                if (version, attr) in self._rollback:
                    del(self._rollback[version, attr])
                continue
            value = getattr(self, attr)
            if value is not None and not isinstance(value, Graph):
                value = type(value)(value)
            self._rollback[version, attr] = value

    def rollback(self, version=None):
        if not hasattr(self, '_rollback'):
            self._rollback = {}
        for attr in self.ROLLBACK_ATTRIBUTES:
            if (version, attr) not in self._rollback:
                if hasattr(self, attr):
                    delattr(self, attr)
                continue
            value = self._rollback[version, attr]
            if value is not None and not isinstance(value, Graph):
                value = type(value)(value)
            setattr(self, attr, value)


class Graph(RollbackMixin):
    ROLLBACK_ATTRIBUTES = {
        'all_edges', 'conditionless_edges', '_conditional_edges',
        'conditional_nodes', 'unconnected',
        '_reachable_from_root', '_root_reachable_from',
        '_edge_reachable_from_root',
        'reduced_graph', 'fg_simplify_cache',
        }

    class Requirement:
        JOINER = 'or'
        global_index = 0

        def __init__(self, parent, label, nodeset=None):
            if nodeset is None:
                nodeset = frozenset()
            self.index = Graph.Requirement.global_index
            Graph.Requirement.global_index += 1
            self.parent = parent
            self.label = label
            self.nodeset = nodeset
            self.set_label(label)
            self.initialize()
            self.validate()

        def __hash__(self):
            return (self.label, self.nodeset).__hash__()

        @property
        def difficult_nodes(self):
            return {self.node}

        def set_label(self, label):
            self.node = self.parent.by_label(label)

        def initialize(self):
            pass

        def validate(self):
            if self.nodeset:
                assert all(isinstance(n, Graph.Node) for n in self.nodeset)
            if isinstance(self, Graph.ComplexRequirement):
                for req in self.parent.requirements:
                    assert req.label != self.label

        def reformat(self):
            return self

        def verify(self):
            import pdb; pdb.set_trace()

        @classmethod
        def preprocess_arguments(self, parent, arguments):
            if arguments is None:
                return None
            arguments = parent.expand_labels(arguments)
            arguments = parent.label_sets_to_nodes(arguments)
            return arguments

        @classmethod
        def get_rtype_from_directive(self, directive):
            if directive.startswith('.'):
                directive = directive[1:]
            for rtype in Graph.REQUIREMENT_TYPES:
                if rtype.DIRECTIVE == directive:
                    break
            else:
                return None
            return rtype

        @classmethod
        def from_line(self, line, parent, autoadd=True):
            while '  ' in line:
                line = line.replace('  ', ' ')
            line = line.strip()
            try:
                directive, label, arguments = line.split(' ', 2)
            except ValueError:
                directive, label = line.split()
                arguments = None

            if not directive.startswith('.'):
                return None
            rtype = self.get_rtype_from_directive(directive)
            if rtype is None:
                raise Exception(f'{line} contains invalid directive.')

            if arguments is None:
                req = rtype(parent, label)
                if autoadd:
                    parent.requirements.add(req)
                return req

            nodesets = rtype.preprocess_arguments(parent, arguments)
            reqs = []
            for nodeset in nodesets:
                if '`NEVER`' in nodeset:
                    req = Graph.Never(parent, label, None)
                else:
                    req = rtype(parent, label, nodeset)
                req = req.reformat()
                reqs.append(req)
            if len(reqs) == 1:
                req = reqs[0]
                if autoadd:
                    parent.requirements.add(req)
                return req
            joiner = self.get_rtype_from_directive(rtype.JOINER)
            joiner = joiner(parent, None, None)
            for req in reqs:
                joiner.add_requirement(req)
            if autoadd:
                parent.requirements.add(joiner)
            return joiner

    class ComplexRequirement(Requirement):
        @property
        def difficult_nodes(self):
            return {n for req in self.requirements
                    for n in req.difficult_nodes}

        def initialize(self):
            self.requirements = set()
            if self.label is None:
                self.label = f'_auto{self.label}{self.index}'

        def add_requirement(self, req):
            self.requirements.add(req)
            req.joiner = self

    class ComplexOr(ComplexRequirement):
        DIRECTIVE = 'or'

        def verify(self):
            msgs = []
            for req in self.requirements:
                try:
                    req.verify()
                    return
                except DoorRouterException as e:
                    msgs.append(e.args[0])
            msg = '\n'.join(msgs)
            raise DoorRouterException(msg)

    class ComplexAnd(ComplexRequirement):
        DIRECTIVE = 'and'

        def verify(self):
            if self in self.parent.requirements:
                raise Exception(
                    '".and" not supported; function is identical to '
                    'multiple simple requirements, but ComplexAnd needs to be '
                    'broken up into its constituent parts for various checks.')

            for req in self.requirements:
                req.verify()

    class FullGuarantee(ComplexRequirement):
        DIRECTIVE = 'full_guarantee'

        @property
        def difficult_nodes(self):
            return {self.node}

        def add_requirement(self, req):
            self.requirements.add(req)
            req.joiner = self
            node = {req.node for req in self.requirements}
            assert len(node) == 1
            node = node.pop()
            if self.node is None:
                self.node = node
            assert self.node is node

        def verify(self):
            if not self.node.rooted:
                return
            for fg in self.node.full_guaranteed:
                guaranteed = self.node.guaranteed | fg
                satisfied = False
                total = set()
                for req in self.requirements:
                    difference = req.nodeset - guaranteed
                    total |= req.nodeset
                    if not difference:
                        satisfied = True
                if not satisfied:
                    difference = total - guaranteed
                    raise DoorRouterException(
                        f'Node {self.node} reachable without {difference}.')

    class Never(Requirement):
        def verify(self):
            raise DoorRouterException(
                    f'Requirement {self.label} is NEVER valid.')

    class Require(Requirement):
        DIRECTIVE = 'require'

        def verify(self):
            if not self.node.rooted:
                return
            if not self.nodeset <= self.parent.rooted:
                raise DoorRouterException(
                    f'Node {self.node} requires {self.nodeset}.')
            self.parent.check_theoretically_reachable(self.nodeset)

            for r in self.nodeset:
                if self.node in r.guaranteed:
                    raise DoorRouterException(
                        f'Node {r} not reachable without {self.node}.')

                corequiring = {req.node for req in self.parent.requirements
                               if isinstance(req, Graph.Require)
                               and req.node.rooted and r in req.nodeset}
                if corequiring <= {self}:
                    continue

                shortest = r.get_shortest_path(avoid_nodes=corequiring)
                if len(corequiring) == 1:
                    assert shortest
                if not shortest:
                    raise DoorRouterException(
                            f'Nodes {corequiring} require {r}.')

    class Guarantee(Requirement):
        DIRECTIVE = 'guarantee'
        JOINER = 'full_guarantee'

        def verify(self):
            if not self.node.rooted:
                return
            self.parent.check_theoretically_reachable(self.nodeset)

            if self.parent.config['lazy_complex_nodes']:
                if self.nodeset <= self.parent.rooted:
                    if all(self.node not in n.guaranteed
                            for n in self.nodeset):
                        return

            difference = self.nodeset - self.node.guaranteed
            if difference:
                raise DoorRouterException(
                    f'Node {self.node} reachable without {difference}.')

    class Missable(Requirement):
        DIRECTIVE = 'missable'

        @property
        def difficult_nodes(self):
            return self.nodeset | {self.node}

        def reformat(self):
            p, l, ns = self.parent, self.label, self.nodeset
            joiner = Graph.ComplexOr(self.parent, None, None)
            joiner.add_requirement(Graph.Unreachable(p, None, ns))
            if self.parent.config['goal_based_missables']:
                joiner.add_requirement(Graph.Nongoal(p, None, ns))
            joiner.add_requirement(Graph.Guarantee(p, l, ns))
            return joiner

        def verify(self):
            raise Exception('Missable.verify() should never be called.')

    class Bridge(Requirement):
        DIRECTIVE = 'bridge'

        def verify(self):
            if not self.node.rooted:
                return

            self.parent.check_theoretically_reachable(self.nodeset,
                                                      partial=True)

            if self.parent.config['lazy_complex_nodes']:
                for n in self.nodeset:
                    if n.rooted and n.rank < self.node.rank:
                        return
                raise DoorRouterException(
                    f'Node {self.node} reachable from wrong direction.')

            edges = {e for e in self.node.reverse_edges
                     if e.source in self.nodeset}
            if not edges & self.node.guaranteed_edges:
                raise DoorRouterException(
                    f'Node {self.node} reachable from wrong direction.')

    class Orphanless(Requirement):
        DIRECTIVE = 'orphanless'

        def initialize(self):
            for e in self.node.reverse_edges:
                assert self.node is e.destination
                e.questionable = True

        def verify(self):
            if not self.node.rooted:
                return
            #for e in self.node.reverse_edges:
            #    assert self.node is e.destination
            #    assert e.questionable
            if self.parent.config['goal_based_missables'] and \
                    self.node not in self.parent.goals_guaranteed and False:
                return
            orphans = {n for n in self.parent.rooted
                       if self.node in n.guaranteed} - {self.node}
            if orphans:
                raise DoorRouterException(
                    f'Node {self.node} must be orphanless.')

    class Tag(Requirement):
        DIRECTIVE = 'tag'

        @classmethod
        def preprocess_arguments(self, parent, arguments):
            arguments = parent.expand_labels(arguments)
            return arguments

        def initialize(self):
            self.node.tags.add(frozenset(self.nodeset))

        def validate(self):
            return

        def verify(self):
            for e in self.node.edges | self.node.reverse_edges:
                if not e.generated:
                    continue
                a, b = (e.source, e.destination)
                assert self.node in (a, b)
                other = ({a, b} - {self.node}).pop()
                if hasattr(other, 'tags'):
                    tags = other.tags
                else:
                    tags = set()
                for nodeset in tags:
                    if self.nodeset == nodeset:
                        break
                else:
                    raise DoorRouterException(
                        f'Node {self.node} needs tags {self.nodeset}.')

    class Unreachable(Requirement):
        DIRECTIVE = 'unreachable'

        @property
        def difficult_nodes(self):
            if self.nodeset:
                dns = set(self.nodeset)
            else:
                dns = set()
            if self.node:
                dns.add(self.node)
            return dns

        def verify(self):
            if self.node and self.node.rooted:
                raise DoorRouterException(
                        f'{self.node} should never be reachable.')
            if self.nodeset and self.nodeset <= self.parent.rooted:
                raise DoorRouterException(
                        f'{self.nodeset} should never be reachable.')

    class Nongoal(Requirement):
        DIRECTIVE = 'nongoal'

        @property
        def difficult_nodes(self):
            if self.nodeset:
                dns = set(self.nodeset)
            else:
                dns = set()
            if self.node:
                dns.add(self.node)
            return dns

        def verify(self):
            if self.node and self.node in self.parent.goals_guaranteed:
                raise DoorRouterException(
                        f'{self.node} should not be required for victory.')
            if self.nodeset and self.nodeset <= self.parent.goals_guaranteed:
                raise DoorRouterException(
                        f'{self.nodeset} should not be required for victory.')

    class ReachableFromWithout(Requirement):
        DIRECTIVE = 'reachable_from_without'

        def __init__(self, parent, label, nodeset):
            self.from_node = nodeset[0]
            assert isinstance(nodeset, list)
            assert len(nodeset) >= 2
            nodeset = frozenset(nodeset[1:])
            super().__init__(parent, label, nodeset)

        @classmethod
        def preprocess_arguments(self, parent, arguments):
            from_nodes, avoid_nodes = arguments.split()
            from_nodes = parent.expand_labels(from_nodes)
            from_nodes = parent.label_sets_to_nodes(from_nodes)
            avoid_nodes = parent.expand_labels(avoid_nodes)
            avoid_nodes = parent.label_sets_to_nodes(avoid_nodes)
            assert len(from_nodes) == 1
            from_nodes = list(from_nodes)[0]
            assert len(from_nodes) == 1
            from_node = list(from_nodes)[0]
            assert isinstance(from_node, Graph.Node)
            arguments = [[from_node] + sorted(avoid_nodeset)
                         for avoid_nodeset in avoid_nodes]
            return arguments

        def verify(self):
            if not self.node.rooted:
                return
            if not self.from_node.rooted:
                raise DoorRouterException(
                        f'{self.node} not reachable from {self.from_node}.')
            rfn = self.from_node.get_naive_avoid_reachable(
                    seek_nodes={self.node}, avoid_nodes=self.nodeset,
                    extra_satisfaction=set(self.from_node.guaranteed))
            if self.node not in rfn:
                raise DoorRouterException(
                        f'{self.node} not reachable from {self.from_node} '
                        f'without {self.nodeset}.')

    class Dependency(Requirement):
        DIRECTIVE = 'dependency'

        def verify(self):
            return

    REQUIREMENT_TYPES = [Require, Guarantee, Missable, Bridge, Orphanless,
                         Tag, Unreachable, Nongoal, ReachableFromWithout,
                         Dependency, ComplexOr, ComplexAnd, FullGuarantee]

    @total_ordering
    class Node(RollbackMixin):
        ROLLBACK_ATTRIBUTES = {
            'edges', 'reverse_edges', 'rank',
            '_rooted', 'prereachable', 'prereachable_from',
            'guar_to', 'full_guar_to', 'strict_full_guar_to', 'edge_guar_to',
            '_free_travel_nodes', '_equivalent_nodes',
            '_free_travel_guaranteed', '_equivalent_guaranteed',
            '_naive_avoid_cache',
            }

        @total_ordering
        class Edge(RollbackMixin):
            ROLLBACK_ATTRIBUTES = {}
            GLOBAL_SORT_INDEX = 0

            def __init__(self, source, destination, condition, procedural,
                         update_caches, questionable=False):
                assert isinstance(source, Graph.Node)
                assert isinstance(destination, Graph.Node)
                assert isinstance(condition, frozenset)
                self.index = Graph.Node.Edge.GLOBAL_SORT_INDEX
                Graph.Node.Edge.GLOBAL_SORT_INDEX += 1

                self.source = source
                self.destination = destination
                self.generated = procedural
                self.questionable = questionable
                graph = self.source.parent

                self.true_condition = set()
                self.false_condition = frozenset()
                if condition:
                    if all(isinstance(l, str) for l in condition):
                        for l in condition:
                            if '`' in l:
                                raise Exception(
                                        'Names cannot contain backticks (`).')
                            if l.startswith('!'):
                                requirements = \
                                    graph.expand_labels(l[1:])
                                assert len(requirements) == 1
                                for req in requirements:
                                    for node in req:
                                        node = \
                                            graph.get_by_label(node)
                                        assert isinstance(node, Graph.Node)
                                        self.false_condition.add(node)
                            else:
                                node = graph.get_by_label(l)
                                self.true_condition.add(node)
                            assert node is not None
                        self.false_condition = frozenset(self.false_condition)
                    else:
                        self.true_condition = set(condition)
                    graph.conditional_nodes |= self.combined_conditions
                    for n in self.combined_conditions:
                        if not n.is_condition:
                            del(n._property_cache['is_condition'])
                    if self.true_condition:
                        self.true_condition = frozenset(
                                self.true_condition - {
                                    self.source, self.source.parent.root})
                self.true_condition = frozenset(self.true_condition)
                if self.false_condition:
                    raise NotImplementedError
                assert self.__hash__() == self.signature.__hash__()

                self.enabled = True

                for e in self.source.edges:
                    if e == self:
                        return

                self.source.edges.add(self)
                self.destination.reverse_edges.add(self)
                graph.all_edges.add(self)
                if self.combined_conditions:
                    del(self._property_cache['combined_conditions'])
                    assert self.source not in self.combined_conditions
                if not self.combined_conditions:
                    graph.conditionless_edges.add(self)
                if update_caches and self.source.rooted:
                    graph.clear_rooted_cache()

                if self.false_condition:
                    raise NotImplementedError(
                        f'False conditions not supported with '
                        f'current optimizations: {self}')

                self.commit()

            def __repr__(self):
                if self.enabled:
                    return self.signature
                else:
                    return f'{self.signature} (DISABLED)'

            def __hash__(self):
                try:
                    return self._hash
                except AttributeError:
                    self._hash = self.signature.__hash__()
                return self.__hash__()

            def __eq__(self, other):
                return self.__hash__() == other.__hash__()

            def __lt__(self, other):
                return self.index < other.index

            @property
            def signature(self):
                questionable = '?' if self.questionable else ''
                if not self.false_condition:
                    s = (f'{self.source}->{self.destination}{questionable}: '
                         f'{sorted(self.true_condition)}')
                else:
                    s = (f'{self.source}->{self.destination}{questionable}: '
                         f'{sorted(self.true_condition)} '
                         f'!{sorted(self.false_condition)}')
                if self.generated:
                    s = f'{s}*'
                return s

            @property
            def rank(self):
                if self.source.rank is not None:
                    if self.true_condition:
                        try:
                            return max(self.source.rank, max(
                                n.rank for n in self.true_condition))
                        except TypeError:
                            return -1
                    return self.source.rank
                return -1

            @cached_property
            def pair(self):
                candidates = {e for e in self.destination.edges if
                              e.destination is self.source and
                              e.true_condition == self.true_condition and
                              e.false_condition == self.false_condition and
                              e.generated == self.generated and
                              e.questionable == self.questionable}
                if not candidates:
                    return None
                assert len(candidates) == 1
                pair = list(candidates)[0]
                return pair

            @property
            def soft_pairs(self):
                candidates = {e for e in self.destination.edges if
                              e.destination is self.source}
                if not candidates:
                    return None
                return candidates

            @cached_property
            def combined_conditions(self):
                return self.true_condition | self.false_condition

            def is_satisfied_by(self, nodes):
                if self.source.parent.config['no_logic']:
                    return True
                if not self.enabled:
                    return False
                if self.true_condition and not (self.true_condition <= nodes):
                    return False
                if self.false_condition and self.false_condition <= nodes:
                    return False
                return True

            def is_satisfied_by_guaranteed(self, guaranteed=None,
                                           full_guaranteed=None):
                if self.source.parent.config['no_logic']:
                    return True
                if guaranteed is None:
                    guaranteed = self.source.guaranteed
                if full_guaranteed is None:
                    full_guaranteed = self.source.full_guaranteed
                if self.is_satisfied_by(guaranteed):
                    assert guaranteed
                    return True
                if not self.enabled:
                    return False
                full_guaranteed = full_guaranteed
                pass_guarantees = set()
                for g in full_guaranteed:
                    if self.is_satisfied_by(g):
                        assert self.true_condition <= g
                        pass_guarantees.add(g)
                if not pass_guarantees:
                    return False
                return pass_guarantees

            def check_is_bridge(self):
                return bool(self.get_guaranteed_orphanable())

            def get_bridge_double_orphanable(self):
                # very slow, accounts for ALL conditions
                g = self.source.parent
                rfr1, rrf1 = (self.source.parent.reachable_from_root,
                              self.source.parent.root_reachable_from)
                self.enabled = False
                self.source.parent.clear_rooted_cache()
                rfr2, rrf2 = (self.source.parent.reachable_from_root,
                              self.source.parent.root_reachable_from)
                self.enabled = True
                self.source.parent.clear_rooted_cache()
                assert rfr1 == self.source.parent.reachable_from_root
                assert rrf1 == self.source.parent.root_reachable_from
                return (rfr1-rfr2), (rrf1-rrf2)

            def get_guaranteed_orphanable(self):
                orphans = {n for n in self.source.parent.rooted
                           if self in self.source.parent.root.edge_guar_to[n]}
                return orphans

            def remove(self):
                self.source.edges.remove(self)
                self.destination.reverse_edges.remove(self)
                self.source.parent.all_edges.remove(self)
                if not self.combined_conditions:
                    self.source.parent.conditionless_edges.remove(self)
                if self.source.rooted:
                    self.source.parent.clear_rooted_cache()
                self.source.parent.changelog.append(('REMOVE', self))

            def bidirectional_remove(self):
                self.remove()
                if self.pair and self.pair is not self:
                    self.pair.remove()

        def __init__(self, label, parent):
            assert label
            if label.endswith('?'):
                raise Exception(f'Node label {label} cannot end with '
                                f'question mark.')
            self.label = label
            self.parent = parent
            if self.parent.root is not None:
                raise NotImplementedError("Can't do this apparently.")

            self._hash = id(self)
            self.rank = None

            self.edges = set()
            self.reverse_edges = set()
            for n in self.parent.nodes:
                assert n.label != self.label
            self.parent.nodes.add(self)

            self.tags = set()

            self.guar_to = {}
            self.full_guar_to = {}
            self.strict_full_guar_to = {}
            self.edge_guar_to = {}

            self.commit()
            self.random_sort_key = md5(
                    f'{self.label}{self.parent.seed}'.encode('ascii')).digest()

        def __repr__(self):
            return self.label

        def __hash__(self):
            return self._hash

        def __eq__(self, other):
            if self is other:
                return True
            if not isinstance(other, Graph.Node):
                if other == '`NEVER`':
                    return False
                assert isinstance(other, Graph.Node)
            if self.parent is not other.parent:
                return False
            assert self.label != other.label
            return False

        def __lt__(self, other):
            return self.label < other.label

        @property
        def double_edges(self):
            return self.edges | self.reverse_edges

        @property
        def rooted(self):
            if hasattr(self, '_rooted'):
                return self._rooted
            return False

        @cached_property
        def is_connectable_node(self):
            return self in self.parent.connectable

        @cached_property
        def is_condition(self):
            return self in self.parent.conditional_nodes

        @cached_property
        def condition_edges(self):
            return frozenset({e for e in self.parent.all_edges
                              if self in e.true_condition})

        @cached_property
        def is_guarantee_condition(self):
            return self in self.parent.guarantee_nodes

        @property
        def is_interesting(self):
            return self in self.parent.interesting_nodes

        @property
        def reverse_nodes(self):
            return {e.source for e in self.reverse_edges} | {self}

        @property
        def dependencies(self):
            if self.parent.config['no_logic']:
                return set()
            dependencies = set()
            for req in self.parent.requirements:
                if not req.node is self:
                    continue
                if type(req) in (Graph.Require, Graph.Guarantee,
                                 Graph.Dependency):
                    dependencies |= req.nodeset
                if isinstance(req, Graph.Bridge) and len(req.nodeset) == 1:
                    dependencies |= req.nodeset
                if isinstance(req, Graph.ReachableFromWithout):
                    dependencies.add(req.from_node)
            return dependencies

        @cached_property
        def required_guarantee(self):
            required_guarantee = set()
            if self.parent.parent is None:
                for req in self.parent.requirements:
                    if hasattr(req, 'joiner') and req.joiner:
                        continue
                    if isinstance(req, Graph.Guarantee) and req.node is self:
                        required_guarantee |= req.nodeset
            else:
                raise Exception('Calculating required_guarantee is '
                                'non-optimal for reduced graphs.')
                nodes = self.parent.node_mapping[self]
                assert not self.parent.requirements
                for req in self.parent.parent.requirements:
                    if hasattr(req, 'joiner') and req.joiner:
                        continue
                    if isinstance(req, Graph.Guarantee) and req.node in nodes:
                        nodeset = {self.parent.node_mapping[n]
                                   for n in req.nodeset}
                        required_guarantee |= nodeset
            return required_guarantee

        @cached_property
        def required_bridges(self):
            if self.parent.parent is not None:
                raise Exception('Calculating required_bridges is '
                                'non-optimal for reduced graphs.')
            required_bridges = set()
            if self.parent.parent is None:
                for req in self.parent.requirements:
                    if hasattr(req, 'joiner') and req.joiner:
                        continue
                    if isinstance(req, Graph.Bridge) and req.node is self:
                        required_bridges |= {e for e in req.node.reverse_edges
                                             if e.source in req.nodeset
                                             and not e.generated}
            return required_bridges

        @cached_property
        def orphanless(self):
            for req in self.parent.requirements:
                if not req.node is self:
                    continue
                if isinstance(req, Graph.Orphanless):
                    return True
            return False

        def get_guaranteed(self):
            try:
                return self.parent.root.guar_to[self]
            except KeyError:
                return None

        def set_guaranteed(self, guaranteed):
            if guaranteed is None:
                del(self.guaranteed)
                return
            self.parent.root.guar_to[self] = guaranteed

        def del_guaranteed(self):
            if self in self.parent.root.guar_to:
                del(self.parent.root.guar_to[self])

        guaranteed = property(get_guaranteed, set_guaranteed, del_guaranteed)

        def get_full_guaranteed(self):
            if self in self.parent.root.full_guar_to:
                return self.parent.root.full_guar_to[self]

        def set_full_guaranteed(self, full_guaranteed):
            if full_guaranteed is None:
                del(self.full_guaranteed)
                return
            if not isinstance(full_guaranteed, frozenset):
                full_guaranteed = frozenset(full_guaranteed)
            self.parent.root.full_guar_to[self] = full_guaranteed

        def del_full_guaranteed(self):
            if self in self.parent.root.full_guar_to:
                del(self.parent.root.full_guar_to[self])

        full_guaranteed = property(
                get_full_guaranteed, set_full_guaranteed, del_full_guaranteed)

        def check_tag_compatibility(self, other):
            if not self.tags and not other.tags:
                return True
            if self.tags & other.tags:
                return True
            return False

        def simplify_full_guaranteed(self):
            if self.guaranteed is None:
                self.guaranteed = frozenset({self})
            if self is self.parent.root and self.full_guaranteed is None:
                self.full_guaranteed = {self.guaranteed}
            self.full_guaranteed = self.parent.simplify_full_guaranteed(
                    {fg | self.guaranteed for fg in self.full_guaranteed})

        def is_superior_guarantee_to(self, fgs):
            smallers, biggers = set(), set()
            combined = fgs | self.full_guaranteed
            for g1 in combined:
                for g2 in combined:
                    if g1 < g2:
                        smallers.add(g1)
                        biggers.add(g2)
            if not (smallers - biggers) <= fgs:
                return False
            if not (biggers - smallers) <= self.full_guaranteed:
                return False
            return True

        def invalidate_guar_to(self):
            assert self is self.parent.root
            if hasattr(self, 'prereachable'):
                del(self.prereachable)

        @property
        def guaranteed_edges(self):
            return self.parent.root.edge_guar_to[self]

        @property
        def free_travel_nodes(self):
            if hasattr(self, '_free_travel_nodes'):
                return self._free_travel_nodes
            free_travel_nodes = frozenset(self.get_free_travel_nodes())
            assert self in free_travel_nodes
            for n in free_travel_nodes:
                n._free_travel_nodes = free_travel_nodes
            return self.free_travel_nodes

        @property
        def equivalent_nodes(self):
            if not hasattr(self.parent, '_reachable_from_root'):
                return self.free_travel_nodes
            if hasattr(self, '_equivalent_nodes'):
                return self._equivalent_nodes
            equivalent_nodes = frozenset(self.get_equivalent_nodes())
            assert self in equivalent_nodes
            for n in equivalent_nodes:
                n._equivalent_nodes = equivalent_nodes
            return self.equivalent_nodes

        @property
        def free_travel_guaranteed(self):
            if hasattr(self, '_free_travel_guaranteed'):
                return self._free_travel_guaranteed
            guaranteed = frozenset.union(
                *[n.guaranteed for n in self.free_travel_nodes])
            for n in self.free_travel_nodes:
                n._free_travel_guaranteed = guaranteed
            return self.free_travel_guaranteed

        @property
        def equivalent_guaranteed(self):
            if not hasattr(self.parent, '_reachable_from_root'):
                return self.free_travel_guaranteed
            if hasattr(self, '_equivalent_guaranteed'):
                return self._equivalent_guaranteed
            if self.guaranteed is None:
                for n in self.equivalent_nodes:
                    assert n.guaranteed is None
                    n._equivalent_guaranteed = None
            else:
                guaranteed = frozenset.union(
                    *[n.guaranteed for n in self.equivalent_nodes])
                for n in self.equivalent_nodes:
                    n._equivalent_guaranteed = guaranteed
            return self.equivalent_guaranteed

        @property
        def connected_nodes(self):
            nodes = {self}
            while True:
                old = set(nodes)
                for n in old:
                    nodes |= {e.destination for e in n.edges}
                    nodes |= {e.source for e in n.reverse_edges}
                if nodes == old:
                    break
            return nodes

        @property
        def generated_edges(self):
            return {e for e in self.all_edges if e.generated}

        def get_by_label(self, label):
            return self.parent.get_by_label(label)

        def by_label(self, label):
            return self.get_by_label(label)

        def add_edge(self, other, condition=None, procedural=False,
                     update_caches=True, questionable=False):
            if condition is None:
                condition = frozenset(set())
            else:
                assert isinstance(condition, frozenset)

            edge = self.Edge(self, other, condition, procedural=procedural,
                             update_caches=update_caches,
                             questionable=questionable)
            for e in self.edges:
                if edge == e and edge is not e:
                    edge = e
            self.parent.changelog.append(('ADD', edge))
            return edge

        def add_edges(self, other, conditions, procedural=False,
                      simplify=True, update_caches=True,
                      force_return_edges=False, questionable=False):
            assert conditions
            edges = set()
            for condition in sorted(conditions, key=lambda c: sorted(c)):
                e = self.add_edge(other, condition, procedural=procedural,
                                  update_caches=update_caches,
                                  questionable=questionable)
                edges.add(e)
            if simplify:
                self.simplify_edges()
            if force_return_edges:
                assert edges
                return edges
            return self.edges & edges

        def simplify_edges(self):
            for edge1 in list(self.edges):
                for edge2 in list(self.edges):
                    if edge1 not in self.edges or edge2 not in self.edges:
                        continue
                    if edge1 is edge2:
                        continue
                    if edge1.destination is not edge2.destination:
                        continue
                    if edge1.false_condition >= edge2.false_condition and \
                            edge1.true_condition <= edge2.true_condition and \
                            edge1.questionable == edge2.questionable:
                        self.edges.remove(edge2)
                        edge2.destination.reverse_edges.remove(edge2)
                        self.parent.all_edges.remove(edge2)

        def get_free_travel_nodes(self):
            if self.is_interesting:
                return {self}
            reachable_nodes = {self}
            reachable_from_nodes = {self}
            edges = set()
            reverse_edges = set()
            done_reachable_nodes = set()
            done_reachable_from_nodes = set()
            done_nodes = set()
            done_edges = set()
            done_reverse_edges = set()
            while True:
                if reachable_nodes == done_reachable_nodes and \
                        reachable_from_nodes == done_reachable_from_nodes:
                    break

                for n in reachable_nodes - done_reachable_nodes:
                    edges |= n.edges
                done_reachable_nodes |= reachable_nodes

                for n in reachable_from_nodes - done_reachable_from_nodes:
                    reverse_edges |= n.reverse_edges
                done_reachable_from_nodes |= reachable_from_nodes

                for e in edges - done_edges:
                    if not (e.destination.is_interesting
                            or e.combined_conditions):
                        reachable_nodes.add(e.destination)
                done_edges |= edges

                for e in reverse_edges - done_reverse_edges:
                    if not (e.source.is_interesting
                            or e.combined_conditions):
                        reachable_from_nodes.add(e.source)
                done_reverse_edges |= reverse_edges

            if hasattr(self, '_free_travel_nodes'):
                free_travel_nodes = reachable_nodes & reachable_from_nodes
                assert self._free_travel_nodes == free_travel_nodes
            return reachable_nodes & reachable_from_nodes

        def get_equivalent_nodes(self):
            if self.is_interesting:
                return {self}
            if not hasattr(self, '_equivalent_nodes'):
                if self.guaranteed is None:
                    return self.free_travel_nodes
                assert self.guaranteed is not None
                for n in self.free_travel_nodes:
                    n._equivalent_nodes = self.free_travel_nodes
            reachable_nodes = set(self.equivalent_nodes)
            old_reachable_nodes = set(reachable_nodes)
            while True:
                edges = {e for n in reachable_nodes for e in n.edges
                         if e.destination.guaranteed is not None
                         and e.destination not in reachable_nodes
                         and not e.destination.is_interesting}
                update = False
                for e in edges:
                    dest = e.destination
                    if e.is_satisfied_by(e.source.equivalent_guaranteed):
                        reverse_edges = {e for e in dest.edges
                                         if e.destination in reachable_nodes}
                        for e2 in reverse_edges:
                            if e2.is_satisfied_by(dest.equivalent_guaranteed):
                                reachable_nodes |= dest.equivalent_nodes
                                update = True
                                break
                    if update:
                        break

                if not update:
                    break

            reachable_nodes = frozenset(reachable_nodes)
            if reachable_nodes != old_reachable_nodes:
                for n in reachable_nodes:
                    n._equivalent_nodes = reachable_nodes
                    if hasattr(n, '_equivalent_guaranteed'):
                        delattr(n, '_equivalent_guaranteed')
                self.get_equivalent_nodes()
            return reachable_nodes

        def propagate_guarantees(self, edges, valid_edges, strict=False):
            root = self.parent.root
            edges = edges & valid_edges
            guar_to = self.guar_to

            strict = strict and self is not root
            if strict:
                full_guar_to = self.strict_full_guar_to
            else:
                full_guar_to = self.full_guar_to

            #done_edges = set()
            #original_edges = frozenset(edges)
            edges = {e for e in edges if e.source in guar_to and
                     e.source in full_guar_to}
            valid_conditional_edges = \
                    valid_edges & self.parent.conditional_edges
            edges_by_node = {}

            while True:
                if not edges:
                    #assert done_edges >= original_edges
                    break

                temp = edges - valid_conditional_edges
                if temp:
                    e = temp.pop()
                    edges.remove(e)
                elif self is root:
                    for e in edges:
                        if all(c.guaranteed is not None
                               for c in e.true_condition):
                            edges.remove(e)
                            break
                    else:
                        raise Exception('No edges for propagation.')
                else:
                    e = edges.pop()

                guaranteed = frozenset(
                        guar_to[e.source] | {e.destination} | e.true_condition)
                gedges = self.edge_guar_to[e.source] | {e}

                if e.destination in full_guar_to:
                    full_guaranteed = full_guar_to[e.source]
                    duaranteed = guar_to[e.destination]
                    dedges = self.edge_guar_to[e.destination]
                    dull_guaranteed = full_guar_to[e.destination]
                    if guaranteed >= duaranteed and \
                            gedges >= dedges:
                        if full_guaranteed <= dull_guaranteed:
                            #done_edges.add(e)
                            continue
                        else:
                            simplified = self.parent.simplify_full_guaranteed(
                                    full_guaranteed | dull_guaranteed)
                            if simplified <= dull_guaranteed:
                                #done_edges.add(e)
                                continue

                if self is root and e.true_condition:
                    special_gedges, special_guaranteed = set(), set()
                    for n in e.true_condition:
                        if n is root:
                            continue
                        # TODO: update full_guaranteed?
                        n_nodes, n_edges = \
                                n.get_guaranteed_reachable_only(strict=False)
                        n.propagate_guarantees(
                                n.edges, n_edges, strict=False)
                        special_gedges |= (n.edge_guar_to[e.source] |
                                           root.edge_guar_to[n])
                        special_guaranteed |= n.guar_to[e.source]

                    if special_gedges and not (gedges >= special_gedges):
                        gedges |= special_gedges
                    if special_guaranteed and \
                            not (guaranteed >= special_guaranteed):
                        guaranteed |= special_guaranteed

                if e.destination not in guar_to:
                    #assert e.destination not in self.edge_guar_to
                    old_gedges = None
                    self.edge_guar_to[e.destination] = frozenset(gedges)
                    old_guar = None
                    guar_to[e.destination] = guaranteed
                else:
                    #assert e.destination in self.edge_guar_to
                    old_gedges = self.edge_guar_to[e.destination]
                    if old_gedges != gedges:
                        self.edge_guar_to[e.destination] = frozenset(
                                old_gedges & gedges)
                    old_guar = guar_to[e.destination]
                    if old_guar != guaranteed:
                        guar_to[e.destination] = guaranteed & old_guar

                full_guaranteed = full_guar_to[e.source]
                temp = guaranteed & self.parent.conditional_nodes
                if temp:
                    for fg in full_guaranteed:
                        if not (fg >= temp):
                            full_guaranteed = frozenset(
                                    {fg | temp for fg in full_guaranteed})
                            break

                if e.destination not in full_guar_to:
                    old_full_guar = None
                    assert isinstance(full_guaranteed, frozenset)
                    full_guar_to[e.destination] = full_guaranteed
                else:
                    old_full_guar = full_guar_to[e.destination]
                    if old_full_guar != full_guaranteed:
                        full_guaranteed = full_guaranteed | old_full_guar
                        full_guar_to[e.destination] = \
                                self.parent.simplify_full_guaranteed(
                                        full_guaranteed)

                #done_edges.add(e)
                old_guaranteed = (old_full_guar, old_gedges, old_guar)
                new_guaranteed = (full_guar_to[e.destination],
                                  self.edge_guar_to[e.destination],
                                  guar_to[e.destination])
                if old_guaranteed != new_guaranteed:
                    if e.destination not in edges_by_node:
                        if e.destination.is_condition:
                            edges_by_node[e.destination] = (
                                (e.destination.edges & valid_edges) |
                                (e.destination.condition_edges
                                 & valid_conditional_edges))
                        else:
                            edges_by_node[e.destination] = \
                                e.destination.edges & valid_edges
                    edges |= edges_by_node[e.destination]
                    if self is root:
                        e.destination.guar_to[e.destination] = \
                                e.destination.guaranteed

        def get_guaranteed_reachable_only(self, seek_nodes=None, strict=False):
            reachable_nodes = {self}
            done_reachable_nodes = set()
            edges = set()
            done_edges = set()
            root = self.parent.root
            if self is root:
                strict = False

            guar_to = self.guar_to
            if strict:
                full_guar_to = self.strict_full_guar_to
            else:
                full_guar_to = self.full_guar_to

            if self.guaranteed is not None:
                guar_to[self] = self.guaranteed
            elif self not in guar_to:
                guar_to[self] = frozenset({self})
            if self not in full_guar_to:
                full_guar_to[self] = frozenset({guar_to[self]})
            if self.full_guaranteed is not None and not strict:
                full_guar_to[self] = full_guar_to[self] | self.full_guaranteed
            full_guar_to[self] = \
                    self.parent.simplify_full_guaranteed(full_guar_to[self])

            self.edge_guar_to[self] = frozenset()
            if self in guar_to:
                assert self in full_guar_to

            if hasattr(self, 'prereachable') and strict in self.prereachable:
                reachable_nodes, done_edges = self.prereachable[strict]
                reachable_nodes = set(reachable_nodes)
                done_edges = set(done_edges)
            else:
                self.prereachable = {}

            done_cascade = set()
            def seek_cascade():
                x = self
                assert seek_nodes is not None
                for n in reachable_nodes - done_cascade:
                    if not hasattr(n, 'prereachable'):
                        continue
                    if strict in n.prereachable:
                        n_pre = n.prereachable[strict]
                    elif True in n.prereachable:
                        n_pre = n.prereachable[True]
                    else:
                        continue
                    n_nodes, n_edges = n_pre
                    seek_n = n_nodes & seek_nodes
                    for sn in seek_n:
                        guar_to[sn] = guar_to[n] | n.guar_to[sn]
                    if seek_n:
                        return seek_n
                done_cascade.update(reachable_nodes)

            cascade = None
            failed_pairs = set()
            updated = False
            counter = 0
            while True:
                if seek_nodes and seek_nodes & reachable_nodes:
                    break

                if seek_nodes:
                    cascade = seek_cascade()
                    if cascade:
                        break

                counter += 1
                todo_nodes = reachable_nodes - done_reachable_nodes
                if not (updated or todo_nodes):
                    break
                for n in todo_nodes:
                    if strict:
                        edges |= {e for e in n.edges if not e.questionable}
                    else:
                        edges |= n.edges
                done_reachable_nodes |= todo_nodes

                updated = False
                todo_edges = edges - done_edges
                temp = {e for e in todo_edges if not e.combined_conditions}
                if temp:
                    todo_edges = temp
                    updated = True
                elif self is root:
                    todo_edges = {e for e in todo_edges
                                  if e.true_condition <= reachable_nodes}

                for e in todo_edges:
                    assert e.enabled
                    guaranteed = guar_to[e.source]
                    full_guaranteed = full_guar_to[e.source]
                    assert isinstance(full_guaranteed, frozenset)
                    if e.source.guaranteed is not None and not strict:
                        guaranteed |= e.source.guaranteed
                        full_guaranteed |= e.source.full_guaranteed
                    result = e.is_satisfied_by_guaranteed(guaranteed,
                                                          full_guaranteed)
                    if result:
                        reachable_nodes.add(e.destination)
                        done_edges.add(e)
                        updated = True
                    else:
                        failed_pairs.add((e.source, e.destination))

                did_edges = done_edges & todo_edges
                if did_edges:
                    assert updated

                self.propagate_guarantees(did_edges, done_edges, strict=strict)

                if strict and not updated:
                    # perform "smart" analysis of node pairs with
                    # multiple edges, using the full guarantee
                    did_edges = set()
                    for source, destination in failed_pairs:
                        if destination in reachable_nodes:
                            continue
                        if source not in root.full_guar_to:
                            continue
                        fail_edges = {e for e in source.edges
                                      if e.destination is destination}
                        if len(fail_edges) < 2:
                            continue
                        fail_guaranteed = guar_to[source]
                        fail_full_guaranteed = root.full_guar_to[source]
                        for ffg in fail_full_guaranteed:
                            for e in fail_edges:
                                if e.is_satisfied_by(fail_guaranteed | ffg):
                                    break
                            else:
                                break
                        else:
                            reachable_nodes.add(destination)
                            did_edges |= fail_edges
                            updated = True
                    done_edges |= did_edges
                    failed_pairs = set()
                    if updated:
                        self.propagate_guarantees(
                                did_edges, done_edges, strict=strict)

            reachable_nodes = frozenset(reachable_nodes)
            done_edges = frozenset(done_edges)
            self.prereachable[strict] = reachable_nodes, done_edges
            if strict and root in reachable_nodes:
                if hasattr(self.parent, '_root_reachable_from') and \
                        self not in self.parent.root_reachable_from:
                    self.parent._root_reachable_from = frozenset(
                            self.parent.root_reachable_from | {self})
                if hasattr(root, 'prereachable_from') and \
                        self not in root.prereachable_from:
                    root.prereachable_from = frozenset(
                            root.prereachable_from | {self})
            if seek_nodes and cascade:
                return frozenset(reachable_nodes | cascade), done_edges
            return reachable_nodes, done_edges

        def get_root_reachable_from(self, reachable_from_root=None):
            assert self is self.parent.root
            if reachable_from_root is None:
                reachable_from_root = self.parent.reachable_from_root
            reachable_from = {self}
            done_reachable_from = set()
            edges = set()
            done_edges = set()
            unreachable = set()

            if hasattr(self, 'prereachable_from'):
                old_fgs = self._rollback[(None, 'full_guar_to')]
                for n in self.prereachable_from:
                    if n not in old_fgs:
                        continue
                    if n.is_superior_guarantee_to(old_fgs[n]):
                        reachable_from.add(n)

            while True:
                todo_nodes = reachable_from - done_reachable_from

                if not todo_nodes:
                    for n in reachable_from_root - reachable_from:
                        test_edges = {e for e in n.edges
                                      if e.destination in reachable_from
                                      and not e.questionable}
                        if not test_edges:
                            continue
                        for fg in n.full_guaranteed:
                            if not any(e for e in test_edges
                                   if e.is_satisfied_by(fg)):
                                break
                        else:
                            assert n not in done_reachable_from
                            reachable_from.add(n)
                            todo_nodes.add(n)

                if not todo_nodes:
                    double_check_nodes = self.parent.conditional_nodes - \
                            (reachable_from | unreachable)
                    for n in double_check_nodes:
                        result_nodes, _ = n.get_guaranteed_reachable_only(
                                seek_nodes=reachable_from, strict=True)
                        if result_nodes & reachable_from:
                            reachable_from.add(n)
                            break
                        else:
                            unreachable.add(n)
                    todo_nodes = reachable_from - done_reachable_from

                if not todo_nodes:
                    break

                for n in todo_nodes:
                    edges |= n.reverse_edges
                done_reachable_from |= todo_nodes

                todo_edges = edges - done_edges
                for e in todo_edges:
                    if e.questionable:
                        continue
                    if e.source in reachable_from:
                        continue
                    guaranteed = e.source.guaranteed
                    if guaranteed is None:
                        guaranteed = {e.source}
                    if e.is_satisfied_by(guaranteed):
                        reachable_from.add(e.source)
                        continue
                done_edges |= todo_edges

            reachable_from = frozenset(reachable_from)
            done_edges = frozenset(done_edges)
            self.prereachable_from = reachable_from
            return reachable_from

        def get_reachable_from(self):
            # brute force reachable_from by getting reachability for each node
            # slow but has some optimization using seek_nodes
            reachable_from = {self}
            for n in self.parent.nodes:
                rfn, _ = n.get_guaranteed_reachable_only(
                        seek_nodes=reachable_from, strict=True)
                if rfn & reachable_from:
                    reachable_from.add(n)
            return frozenset(reachable_from)

        def get_guaranteed_reachable(self, and_from=False, do_reduce=None,
                                     strict=True, seek_nodes=None):
            xrf = None
            if do_reduce is None:
                do_reduce = self.parent.reduce and \
                        bool(self.parent.reduced_graph)
            if not do_reduce:
                rfx, erfx = self.get_guaranteed_reachable_only(
                        strict=strict, seek_nodes=seek_nodes)
                if and_from:
                    if self is self.parent.root:
                        xrf = self.get_root_reachable_from(rfx)
                    else:
                        xrf = self.get_reachable_from()
                return rfx, xrf, erfx

            if not (hasattr(self.parent, 'reduced_graph')
                    and self.parent.reduced_graph is not None):
                self.parent.reduced_graph = self.parent.get_reduced_graph()
            rgraph = self.parent.reduced_graph
            rgraph.reachable_from_root

            counterpart = rgraph.node_mapping[self]
            rfx, erfx = counterpart.get_guaranteed_reachable_only(
                    strict=strict, seek_nodes=seek_nodes)
            if and_from:
                if self is self.parent.root:
                    xrf = counterpart.get_root_reachable_from(rfx)
                else:
                    xrf = counterpart.get_reachable_from()

            rfx = rgraph.remap_nodes(rfx)
            if xrf is not None:
                xrf = rgraph.remap_nodes(xrf)
                if self is self.parent.root:
                    self.prereachable_from = frozenset(xrf)

            erfx = frozenset(rgraph.remap_edges(erfx))
            return rfx, xrf, erfx

        def get_shortest_path(self, other=None, extra_satisfaction=None,
                              avoid_nodes=None, avoid_edges=None):

            if other is None:
                return self.parent.root.get_shortest_path(
                        other=self, extra_satisfaction=extra_satisfaction,
                        avoid_nodes=avoid_nodes, avoid_edges=avoid_edges)
            if self is other:
                return []
            if not self.rooted and other.rooted:
                raise Exception('Can only calculate paths of rooted nodes.')

            if isinstance(avoid_nodes, Graph.Node):
                avoid_nodes = frozenset({avoid_nodes})
            elif isinstance(avoid_nodes, set) and \
                    not isinstance(avoid_nodes, frozenset):
                avoid_nodes = frozenset(avoid_nodes)
            elif not avoid_nodes:
                avoid_nodes = frozenset()

            if isinstance(avoid_edges, Graph.Node.Edge):
                avoid_edges = frozenset({avoid_edges})
            elif not avoid_edges:
                avoid_edges = frozenset()

            if extra_satisfaction is None:
                extra_satisfaction = set()
            if self.guaranteed is not None:
                satisfaction = self.parent.conditional_nodes & (
                        self.guaranteed | extra_satisfaction)
            else:
                satisfaction = self.parent.conditional_nodes & \
                        extra_satisfaction
            satisfaction -= avoid_nodes

            rfn, _, _ = self.get_guaranteed_reachable()
            if other not in rfn:
                return None

            # fast but fails against double one-way conditions?
            nodes = {self}
            done_nodes = set()
            edges = set()
            done_edges = set(avoid_edges)

            rank = 0
            rank_dict = {}
            while True:
                for n in nodes - done_nodes:
                    assert n not in rank_dict
                    rank_dict[n] = rank
                    edges |= n.edges
                if other in nodes:
                    break
                rank += 1
                done_nodes |= nodes
                for e in edges - done_edges:
                    if e.destination in avoid_nodes:
                        continue
                    if e.is_satisfied_by(satisfaction | done_nodes):
                        nodes.add(e.destination)
                        done_edges.add(e)
                if not nodes - done_nodes:
                    break

            def get_recurse_edges(n):
                reverse_edges = {e for e in n.reverse_edges
                                 if e.source in rank_dict
                                 and e not in avoid_edges
                                 and e.source not in avoid_nodes
                                 and e.true_condition <= self.parent.rooted
                                 and ((not e.true_condition) or
                                      (not e.true_condition &
                                       e.get_guaranteed_orphanable()))}
                return reverse_edges

            def shortest_recurse(n):
                if n is self:
                    return []
                reverse_edges = {e for e in get_recurse_edges(n)
                                 if rank_dict[n] > rank_dict[e.source]}
                paths = [(e, shortest_recurse(e.source))
                         for e in reverse_edges]
                paths = [(e, p) for (e, p) in paths if p is not None]
                if not paths:
                    return None
                e, shortest = min(paths, key=lambda x: (len(x[1]), x))
                return shortest + [e]

            return shortest_recurse(other)

        def get_naive_avoid_reachable(
                self, seek_nodes=None, avoid_nodes=None, avoid_edges=None,
                extra_satisfaction=None, recurse_depth=0):
            if not hasattr(self, '_naive_avoid_cache'):
                self._naive_avoid_cache = {}
            MAX_RECURSE_DEPTH = 2
            if seek_nodes is None:
                seek_nodes = frozenset()
            if avoid_nodes is None:
                avoid_nodes = frozenset()
            if avoid_edges is None:
                avoid_edges = frozenset()
            if extra_satisfaction is None:
                extra_satisfaction = set()

            extra_satisfaction &= self.parent.conditional_nodes
            seek_nodes = frozenset(seek_nodes)
            avoid_nodes = frozenset(avoid_nodes)
            avoid_edges = frozenset(avoid_edges)
            original_extra = frozenset(extra_satisfaction)

            cache_key = (avoid_nodes, avoid_edges, original_extra,
                         recurse_depth, seek_nodes)
            if cache_key in self._naive_avoid_cache:
                return self._naive_avoid_cache[cache_key]
            for other_key in self._naive_avoid_cache:
                (other_nodes, other_edges, other_extra,
                        other_recurse, other_seek) = other_key
                if other_nodes == avoid_nodes and \
                        other_edges == avoid_edges and \
                        other_extra == original_extra and \
                        other_recurse <= recurse_depth and \
                        other_seek <= seek_nodes:
                    return self._naive_avoid_cache[other_key]
                if avoid_nodes - other_nodes:
                    continue
                if avoid_edges - other_edges:
                    continue
                if seek_nodes and \
                        seek_nodes & self._naive_avoid_cache[other_key] and \
                        other_extra <= original_extra:
                    return seek_nodes & self._naive_avoid_cache[other_key]

            guar_to = {n: (self.guaranteed | n.guaranteed)
                       for n in self.parent.rooted}
            nodes = {self}
            done_nodes = set(avoid_nodes)
            edges = set()
            done_edges = set(avoid_edges)

            want_nodes = set()
            done_want_nodes = set()
            reachable_from = defaultdict(set)
            updated = False
            while True:
                if nodes & seek_nodes:
                    break

                todo_nodes = nodes - (done_nodes | avoid_nodes)
                if recurse_depth < MAX_RECURSE_DEPTH and not todo_nodes:
                    double_check_nodes = (nodes & want_nodes) \
                            - (extra_satisfaction | avoid_nodes
                                    | done_want_nodes)
                    for n in double_check_nodes:
                        test = n.get_naive_avoid_reachable(
                                seek_nodes={self},
                                avoid_nodes=avoid_nodes,
                                avoid_edges=avoid_edges,
                                extra_satisfaction=set(self.guaranteed),
                                recurse_depth=recurse_depth+1)
                        if self in test:
                            updated = True
                            extra_satisfaction.add(n)
                        for n2 in test:
                            if n not in reachable_from[n2]:
                                reachable_from[n2].add(n)
                                updated = True
                        done_want_nodes.add(n)

                if not (todo_nodes or updated):
                    break
                updated = False

                for n in todo_nodes:
                    edges |= (n.edges - avoid_edges)
                done_nodes |= todo_nodes

                todo_edges = edges - (done_edges | avoid_edges)
                for e in todo_edges:
                    if e.destination in avoid_nodes:
                        continue
                    guaranteed = guar_to[e.source]
                    if e.is_satisfied_by(guaranteed | extra_satisfaction
                                         | reachable_from[e.source]):
                        nodes.add(e.destination)
                        done_edges.add(e)
                    else:
                        want_nodes |= e.true_condition

            self._naive_avoid_cache[cache_key] = nodes
            return nodes

        def verify_required(self):
            if self.parent.config['no_logic']:
                return
            for req in self.parent.requirements:
                if req.node is self and isinstance(req, self.parent.Require):
                    req.verify()
            return

    def __init__(self, filename=None, config=None, preset_connections=None,
                 strict_validator=None, lenient_validator=None,
                 testing=False, do_reduce=None, parent=None,
                 definition_overrides=None, infer_nodes=True):
        self.testing = testing
        self.parent = parent
        if do_reduce is not None:
            self.reduce = do_reduce
        else:
            self.reduce = REDUCE and not self.parent
        self.infer_nodes = infer_nodes

        if config is None:
            if filename is None:
                filename = DEFAULT_CONFIG_FILENAME
            with open(filename) as f:
                self.config = yaml.safe_load(f.read())
            self.config['config_filename'] = filename
        else:
            self.config = config
        with open(DEFAULT_CONFIG_FILENAME) as f:
            defaults = yaml.load(f.read())
        for key in defaults:
            if key not in self.config:
                self.config[key] = defaults[key]
                print(f'Using default value {defaults[key]} for "{key}".')

        self.strict_validator = strict_validator
        self.lenient_validator = lenient_validator
        self.definition_overrides = definition_overrides

        self.fg_simplify_cache = {}

        if preset_connections is None:
            preset_connections = {}
        self.preset_connections = preset_connections
        if 'seed' in self.config:
            self.seed = self.config['seed']
        elif self.parent:
            self.seed = (-abs(self.parent.seed)) - 1
        elif self.testing:
            self.seed = 0
        else:
            self.seed = random.randint(0, 9999999999)

        self.PREINITIALIZE_ATTRS = set()
        self.PREINITIALIZE_ATTRS = frozenset(self.PREINITIALIZE_ATTRS
                                             | set(dir(self)))
        if self.testing or self.parent:
            self.initialize_empty()
        else:
            self.initialize()

    @property
    def description(self):
        s = ''
        s += 'Maze Generation Settings:\n'
        s += f'  seed:{"":16} {self.seed}\n'
        if hasattr(self, 'attempts'):
            s += f'  attempts:{"":12} {self.attempts}\n'
        for key, value in self.config.items():
            if key == 'seed':
                continue
            key = f'{key}:'
            s += f'  {key:21} {value}\n'
        if self.num_loops > 0:
            s += f'\nCharacteristics:\n'
            key = 'longest path:'
            try:
                value = max(n.rank for n in self.nodes if n.rank is not None)
            except ValueError:
                value = -1
            s += f'  {key:21} {value}\n'
            if self.goal_reached and (self.root_reachable_from >=
                                      self.reachable_from_root):
                if not hasattr(self, 'solutions'):
                    self.generate_solutions()
                key = 'longest win path:'
                value = self.solutions[-1][1][-1].destination.rank
                s += f'  {key:21} {value}\n'
                required_nodes = set()
                for _, path in self.solutions:
                    required_nodes |= {p.destination for p in path}
                    required_nodes &= self.connectable
                key = 'required nodes:'
                value = len(required_nodes)
                s += f'  {key:21} {value}\n'
            key = 'total nodes:'
            value = len(self.rooted & self.initial_unconnected)
            value = f'{value}/{len(self.rooted)}'
            s += f'  {key:21} {value}\n'
            key = 'generated edges:'
            value = len({e for e in self.all_edges if e.generated
                         and e.pair and e.source < e.destination})
            s += f'  {key:21} {value}\n'
            key = 'static edges:'
            value = len({e for e in self.all_edges if (not e.generated)
                         and e.pair and e.source < e.destination})
            s += f'  {key:21} {value}\n'
            key = 'generation loops:'
            value = self.num_loops
            s += f'  {key:21} {value}\n'

        return s.strip()

    @property
    def description_problematic(self):
        s1 = self.description
        s2 = 'Problematic Nodes:\n'
        pnodes = sorted([(v, k) for (k, v) in self.problematic_nodes.items()
                         if v > 0], reverse=True)
        for count, node in pnodes[:10]:
            s2 += f'  {count:>4} {node}\n'
        return f'{s1}\n\n{s2}'.strip()

    def initialize_empty(self):
        self.root = None
        self.nodes = set()
        self.all_edges = set()
        self.conditionless_edges = set()
        self.connectable = set()
        self.conditional_nodes = set()
        self.all_dependencies = set()
        self.problematic_nodes = defaultdict(int)
        self.num_loops = -1
        self.definitions = {}
        self.changelog = []
        self.requirements = set()

    def initialize(self):
        self.changelog = []
        random.seed(self.seed)
        self.initialize_empty()

        nodes_filename = self.config['nodes_filename']
        try:
            lines = read_lines_nocomment(nodes_filename)
        except FileNotFoundError:
            from .tablereader import tblpath
            nodes_filename = path.join(tblpath, nodes_filename)
            lines = read_lines_nocomment(nodes_filename)

        for line in read_lines_nocomment(nodes_filename):
            if line.startswith('+'):
                self.Node(line[1:], self)
            else:
                self.connectable.add(self.Node(line, self))
        self.connectable = frozenset(self.connectable)

        logic_filename = self.config['logic_filename']
        try:
            lines = read_lines_nocomment(logic_filename)
        except FileNotFoundError:
            from .tablereader import tblpath
            logic_filename = path.join(tblpath, logic_filename)
            lines = read_lines_nocomment(logic_filename)

        newlines = []
        for line in lines:
            while '  ' in line:
                line = line.replace('  ', ' ')
            newlines.append(line.strip())
        lines = newlines

        predefinitions = {}
        for line in lines:
            if not line.startswith('.def'):
                continue

            _, definition_label, requirements = line.split(' ')
            if definition_label in self.definition_overrides:
                predefinitions[definition_label] = \
                        self.definition_overrides[definition_label]
            else:
                predefinitions[definition_label] = requirements

        if self.infer_nodes:
            for line in lines:
                if line.startswith('.'):
                    continue
                line = line.split()[0]
                for operator in ['>>', '=>', '<<', '<=', '=', '>', '<']:
                    if operator in line:
                        for n in line.split(operator):
                            if '*' in n:
                                continue
                            if n.endswith('?'):
                                n = n.rstrip('?')
                            if n in predefinitions:
                                continue
                            if self.get_by_label(n) is None:
                                self.Node(n, self)
                        break

        self.unconnected = self.connectable - {
                self.get_by_label(l) for l in self.preset_connections.keys()}

        dependencies = defaultdict(set)
        for key1, value in predefinitions.items():
            for key2 in sorted(predefinitions.keys(),
                               key=lambda k2: (-len(k2), k2)):
                if key1 == key2:
                    continue
                if key2 in value:
                    value = value.replace(key2, '')
                    dependencies[key1].add(key2)

        while True:
            updated = False
            for key1 in sorted(dependencies):
                for key2 in sorted(dependencies[key1]):
                    if key1 in dependencies[key2]:
                        raise Exception(f'Circular dependency: {key1}, {key2}')
                    if dependencies[key2] - dependencies[key1]:
                        dependencies[key1] |= dependencies[key2]
                        updated = True
            if not updated:
                break

        assert len(self.definitions) == 0
        while True:
            done_definitions = set(self.definitions.keys())
            if done_definitions >= set(predefinitions.keys()):
                break
            nextdefs = {d for d in predefinitions
                        if dependencies[d] <= done_definitions}
            nextdefs -= done_definitions
            assert nextdefs
            for d in nextdefs:
                self.definitions[d] = frozenset(
                        self.expand_labels(predefinitions[d]))

        for line in lines:
            if line.startswith('.def'):
                continue

            for definition_label in self.definitions:
                if definition_label in line:
                    sub = self.definitions[definition_label]
                    if len(sub) == 1:
                        sub = list(sub)[0]
                        if len(sub) == 1:
                            sub = list(sub)[0]
                            test = [sub if w == definition_label else w
                                    for w in line.split()]
                            line = ' '.join(test)

            if line.startswith('.start'):
                _, root_label = line.split(' ')
                self.set_root(self.get_by_label(root_label))
                continue

            if line.startswith('.goal'):
                _, requirements = line.split(' ')
                requirements = self.expand_labels(requirements)
                self.set_goal(requirements)
                continue

            complex_requirement = None
            if line.startswith('+'):
                reqlabel, line = line.split(' ', 1)
                assert reqlabel.startswith('+')
                reqlabel = reqlabel[1:]
                for req in self.requirements:
                    if not (isinstance(req, self.ComplexOr)
                            or isinstance(req, self.ComplexAnd)):
                        continue
                    if req.label == reqlabel:
                        complex_requirement = req
                        break

            if line.startswith('.'):
                req = self.Requirement.from_line(line, self, autoadd=False)
                if req is not None:
                    if complex_requirement is not None:
                        assert complex_requirement in self.requirements
                        complex_requirement.add_requirement(req)
                    else:
                        self.requirements.add(req)
                    continue

            assert not line.startswith('.')

            if ' ' in line:
                edge, conditions = line.split()
                conditions_label = conditions
                conditions = self.expand_labels(conditions)
            else:
                edge = line
                conditions = set()

            if '<' in edge:
                if '<=' in edge:
                    edge = '=>'.join(reversed(edge.split('<=')))
                elif '<<' in edge:
                    edge = '>>'.join(reversed(edge.split('<<')))
                else:
                    edge = '>'.join(reversed(edge.split('<')))
            assert '<' not in edge

            if len(conditions) == 0:
                conditions = {frozenset()}
            if '=' in edge:
                a, b = edge.split('=')
                if a == b:
                    req = self.Requirement.from_line(
                        f'.tag {a} {conditions_label}', self)
            self.add_multiedge(edge, conditions)

        difficult_nodes = {n for req in self.requirements
                           for n in req.difficult_nodes}
        if self.preset_connections is not None:
            for alabel in self.preset_connections:
                a = self.get_by_label(alabel)
                for blabel, conditions in self.preset_connections[alabel]:
                    b = self.get_by_label(blabel)
                    if self.config['skip_complex_nodes'] >= 1 \
                            and {a, b} & difficult_nodes:
                        print(f'Warning: Fixed exit {a} -> {b} violates '
                              f'complex node policy. Removing this exit.')
                        self.unconnected |= {a, b}
                        continue
                    if not conditions:
                        edges = {e for e in a.edges if e.destination is b
                                 and not e.true_condition}
                        if edges:
                            continue
                    assert a in self.connectable
                    assert b in self.connectable
                    assert a not in self.unconnected
                    #assert b not in self.unconnected
                    a.add_edge(b, conditions)

        def mini_naive_reachable_from(node):
            reachable_from = {node}
            while True:
                old = set(reachable_from)
                for n in old:
                    for e in n.reverse_edges:
                        if e.true_condition:
                            continue
                        reachable_from.add(e.source)
                if reachable_from == old:
                    break
            return reachable_from

        def mini_condition_reachable_from(node):
            reachable_from = mini_naive_reachable_from(node)
            reachable = set(reachable_from)
            necessary = set()
            while True:
                if reachable & reachable_from & self.unconnected:
                    break
                old = set(reachable_from)
                for n in old:
                    for e in n.reverse_edges:
                        if e.true_condition:
                            necessary |= e.true_condition
                        reachable_from.add(e.source)
                for n in old:
                    for e in n.edges:
                        if e.true_condition <= necessary:
                            reachable.add(e.destination)
                if reachable_from == old:
                    break
            return reachable_from, necessary

        necessary_nodes = set(self.goal_nodes)
        necessary_nodes.add(self.root)
        while True:
            old = set(necessary_nodes)
            for n in old:
                necessary_nodes |= n.dependencies
                reachable = mini_naive_reachable_from(n)
                if self.root in reachable:
                    continue
                if n in self.goal_nodes and not reachable & self.unconnected:
                    more_reach, necessary = mini_condition_reachable_from(n)
                    necessary_nodes |= more_reach | necessary
                necessary_nodes |= reachable
            if necessary_nodes == old:
                break

        assert self.unconnected <= self.connectable <= self.nodes
        num_nodes = int(round(self.config['map_size'] * len(self.unconnected)))
        reduced = necessary_nodes & self.unconnected
        too_complex = set()
        for n in sorted(difficult_nodes - necessary_nodes):
            if random.random() > self.config['skip_complex_nodes']:
                continue
            too_complex.add(n)
        assert not too_complex & necessary_nodes

        while True:
            old = set(too_complex)
            for n in old:
                for e in n.reverse_edges:
                    too_complex.add(e.source)
            if too_complex == old:
                break

        too_complex -= necessary_nodes

        reduced = necessary_nodes & self.unconnected
        for n in self.goal_nodes:
            test = mini_naive_reachable_from(n)
            if self.root in test:
                continue
            if test & reduced:
                continue
            more_test, _ = mini_condition_reachable_from(n)
            if more_test & reduced:
                continue
            raise Exception(f'Node {n} has no access point.')

        while True:
            assert not reduced & too_complex
            candidates = sorted(self.unconnected - (too_complex | reduced))
            if not candidates:
                break
            chosen = random.choice(candidates)
            backup_reduced = set(reduced)
            reduced.add(chosen)
            while True:
                old_reduced = set(reduced)
                for n in old_reduced:
                    for e in n.edges:
                        if e.true_condition & too_complex:
                            continue
                        if e.destination in too_complex:
                            continue
                        reduced.add(e.destination)
                        reduced |= e.true_condition
                    reduced |= n.dependencies
                if reduced == old_reduced:
                    break
            if (reduced - backup_reduced) & too_complex:
                too_complex.add(chosen)
                reduced = backup_reduced
                continue
            if len(reduced & self.unconnected) >= num_nodes:
                break

        assert not reduced & too_complex
        for n in reduced:
            assert n.dependencies <= reduced
            self.all_dependencies |= n.dependencies

        self.allow_connecting = frozenset(reduced & self.connectable)
        assert necessary_nodes & self.unconnected == \
                necessary_nodes & reduced & self.unconnected
        self.unconnected = reduced & self.unconnected
        self.initial_unconnected = frozenset(self.unconnected)

        theoretically_reachable = set(self.initial_unconnected) | {self.root}
        while True:
            old = set(theoretically_reachable)
            for n in old:
                for e in n.edges:
                    if e.true_condition <= old:
                        theoretically_reachable.add(e.destination)
            if theoretically_reachable == old:
                break
        self.theoretically_reachable = frozenset(theoretically_reachable)
        self.nodes = frozenset(self.nodes)

        assert self.unconnected <= self.allow_connecting <= \
                self.connectable <= self.nodes
        del(self._property_cache)
        assert self.unconnected & self.rooted

        self.verify()
        self.commit()


    def reinitialize(self):
        random.seed(self.seed)
        self.seed = random.randint(0, 9999999999)
        post_initialize_attrs = set(dir(self)) - self.PREINITIALIZE_ATTRS
        for attr in post_initialize_attrs:
            delattr(self, attr)
        self.initialize()

    @property
    def rooted(self):
        return self.reachable_from_root

    @property
    def double_rooted(self):
        return self.reachable_from_root & self.root_reachable_from

    @property
    def reachable_from_root(self):
        if hasattr(self, '_reachable_from_root'):
            return self._reachable_from_root

        if DEBUG:
            print('FIND REACHABLE FROM ROOT')

        def getroll(x, attr, duplicate=True):
            key = (None, attr)
            if hasattr(x, '_rollback') and key in x._rollback:
                value = x._rollback[key]
                if duplicate and value is not None:
                    value = type(value)(value)
                return value
            return None

        roll_edges = getroll(self, 'all_edges', duplicate=False)
        if roll_edges and not (self.all_edges >= roll_edges):
            roll_edges = None
        if roll_edges and self.parent is not None:
            roll_edges = None
        if roll_edges is not None:
            assert not hasattr(self, 'reduced_graph')
            self.reduced_graph = None
            old_rfr = getroll(self, '_reachable_from_root')
            if old_rfr is None:
                old_rfr = set()
            for n in self.nodes & old_rfr:
                for attr in ['guar_to', 'edge_guar_to', 'rank',
                             'full_guar_to', 'strict_full_guar_to',
                             'prereachable', 'prereachable_from']:
                    value = getroll(n, attr)
                    if value is None:
                        continue
                    setattr(n, attr, value)
            self.root.invalidate_guar_to()
            rfr, rrf, erfr = self.root.get_guaranteed_reachable(
                    and_from=True, do_reduce=False)
        elif self.reduce:
            self.reduced_graph = self.get_reduced_graph()
            rfr, rrf, erfr = self.root.get_guaranteed_reachable(
                    and_from=True, do_reduce=True)
        else:
            self.reduced_graph = None
            rfr, rrf, erfr = self.root.get_guaranteed_reachable(
                    and_from=True, do_reduce=False)

        self._reachable_from_root = rfr
        self._root_reachable_from = rrf
        self._edge_reachable_from_root = erfr
        for e in self._edge_reachable_from_root:
            assert e.source.parent is self
            assert e.destination.parent is self
            for n in e.true_condition:
                assert n.parent is self

        unrooted = self.nodes - rfr
        for n in rfr:
            n._rooted = True
        for n in unrooted:
            n._rooted = False

        if roll_edges:
            self.rerank()
        elif self.reduced_graph is not None:
            self.reduced_graph.rerank()
            self.rerank_and_reguarantee()
        else:
            self.rerank()

        self.cleanup_guarantees()

        assert self.root in self.reachable_from_root
        assert self.root in self.root_reachable_from
        for n in self.root_reachable_from - self.reachable_from_root:
            assert not n.full_guaranteed

        assert self._reachable_from_root
        assert self._root_reachable_from
        return self.reachable_from_root

    @property
    def root_reachable_from(self):
        if hasattr(self, '_root_reachable_from'):
            return self._root_reachable_from
        self.reachable_from_root
        return self.root_reachable_from

    @property
    def goal_reached(self):
        num_connected = len(self.initial_unconnected) - len(self.unconnected)
        if num_connected / len(self.initial_unconnected) < \
                self.config['map_strictness'] and len(self.unconnected) > 1:
            return False
        for condition in self.goal:
            if condition < self.double_rooted:
                return True
        return False

    @cached_property
    def goal_nodes(self):
        goal_nodes = set()
        for condition in self.goal:
            for n in condition:
                goal_nodes.add(n)
                goal_nodes |= n.dependencies
        return goal_nodes

    @property
    def goals_guaranteed(self):
        return self.expand_guaranteed(self.goal_nodes & self.rooted) \
                | self.goal_nodes

    @property
    def interesting_nodes(self):
        return self.conditional_nodes | self.all_dependencies | {self.root}

    @property
    def conditional_edges(self):
        if hasattr(self, '_conditional_edges'):
            return self._conditional_edges
        self._conditional_edges = self.all_edges - self.conditionless_edges
        return self.conditional_edges

    def get_by_label(self, label):
        for n in self.nodes:
            if n.label == label:
                return n

    def by_label(self, label):
        return self.get_by_label(label)

    def set_root(self, node):
        assert node in self.nodes
        self.root = node
        node.strict_full_guar_to = None
        self.clear_rooted_cache()

    def set_goal(self, conditions):
        self.goal = frozenset({frozenset(self.get_by_label(l) for l in c)
                               for c in conditions})

    def clear_rooted_cache(self):
        cleared = False
        for attr in ('_reachable_from_root', '_root_reachable_from',
                     '_edge_reachable_from_root',
                     'reduced_graph', 'reduced_edge_ranks'):
            if hasattr(self, attr):
                if getattr(self, attr):
                    cleared = True
                delattr(self, attr)
        for node in self.nodes:
            for attr in ('_rooted', 'prereachable', 'prereachable_from',
                         '_free_travel_nodes', '_equivalent_nodes',
                         '_free_travel_guaranteed', '_equivalent_guaranteed',
                         '_naive_avoid_cache'):
                if hasattr(node, attr):
                    delattr(node, attr)
        self.clear_node_guarantees()
        if DEBUG and cleared:
            print(self.num_loops, 'CLEAR ROOT')

    def clear_node_guarantees(self):
        for n in self.nodes:
            if hasattr(n, '_rooted'):
                delattr(n, '_rooted')
            n.rank = None
            n.guar_to = {}
            n.full_guar_to = {}
            n.strict_full_guar_to = {}
            n.edge_guar_to = {}
        self.fg_simplify_cache = {}
        self.root.strict_full_guar_to = None

    def simplify_full_guaranteed(self, full_guaranteed):
        if not isinstance(full_guaranteed, frozenset):
            full_guaranteed = frozenset(full_guaranteed)
        if full_guaranteed in self.fg_simplify_cache:
            return self.fg_simplify_cache[full_guaranteed]
        original = full_guaranteed
        if len(self.fg_simplify_cache) > self.config['fg_cache_limit']:
            self.fg_simplify_cache = {}
        for fg in full_guaranteed:
            for g in fg:
                if not g.is_condition:
                    full_guaranteed = frozenset({g & self.conditional_nodes
                                                 for g in full_guaranteed})
                    break
            else:
                continue
            break
        if len(full_guaranteed) < 3:
            self.fg_simplify_cache[original] = full_guaranteed
            self.fg_simplify_cache[full_guaranteed] = full_guaranteed
            return full_guaranteed
        smallers, biggers = set(), set()
        for g1 in full_guaranteed:
            for g2 in full_guaranteed:
                if g1 < g2:
                    smallers.add(g1)
                    biggers.add(g2)
        if smallers and biggers:
            mediums = smallers & biggers
            if mediums:
                full_guaranteed = full_guaranteed - mediums
        self.fg_simplify_cache[original] = full_guaranteed
        self.fg_simplify_cache[full_guaranteed] = full_guaranteed
        return full_guaranteed

    def expand_guaranteed(self, guaranteed):
        while True:
            new_guaranteed = {n2 for n1 in guaranteed for n2 in n1.guaranteed}
            if new_guaranteed == guaranteed:
                break
            guaranteed = new_guaranteed
        if not isinstance(guaranteed, frozenset):
            guaranteed = frozenset(guaranteed)
        return guaranteed

    def cleanup_guarantees(self):
        rfr = self.reachable_from_root
        expand_cache = {}

        def expand(nodes):
            if nodes in expand_cache:
                return expand_cache[nodes]
            expand_cache[nodes] = \
                    frozenset({n2 for n1 in nodes for n2 in n1.guaranteed})
            return expand(nodes)

        for n in sorted(rfr, key=lambda x: x.rank):
            for g in n.guaranteed:
                assert g is n or g.rank < n.rank
            n.guaranteed = frozenset({n2 for n1 in n.guaranteed
                                      for n2 in n1.guaranteed})
            n.guaranteed = expand(n.guaranteed)
            if n in n.guar_to:
                assert n.guar_to[n] <= n.guaranteed
            n.guar_to[n] = n.guaranteed

        for n in sorted(rfr, key=lambda x: x.rank):
            n.full_guaranteed = self.simplify_full_guaranteed(
                {expand(fg) for fg in n.full_guaranteed})

    def expand_labels(self, requirements):
        original = str(requirements)
        assert isinstance(requirements, str)
        if requirements.startswith('suggest:'):
            return frozenset(set())
        if '&' in requirements:
            assert '|' not in requirements
            requirements = requirements.split('&')
            requirements = [self.definitions[r] if r in self.definitions
                            else {frozenset({r})} for r in requirements]
            while len(requirements) >= 2:
                a = requirements[0]
                b = requirements[1]
                if not a and b:
                    raise Exception(f'Condition {original} failed '
                                    f'because one side is null.')
                requirements = requirements[2:]
                r = set()
                for aa in a:
                    for bb in b:
                        r.add(frozenset(aa | bb))
                requirements.append(r)
            assert len(requirements) == 1
            result = set(requirements[0])
        else:
            assert '&' not in requirements
            result = set()
            requirements = requirements.split('|')
            for r in requirements:
                if r in self.definitions:
                    defined = self.definitions[r]
                    assert isinstance(defined, frozenset)
                    for r in defined:
                        assert isinstance(r, frozenset)
                        result.add(r)
                else:
                    result.add(frozenset({r}))
        for r in sorted(result):
            for compare in sorted(result):
                if r < compare and compare in result:
                    result.remove(compare)
        return result

    def label_sets_to_nodes(self, label_sets):
        if not label_sets:
            return label_sets
        if isinstance(list(label_sets)[0], str):
            for l in label_sets:
                if l == '`NEVER`':
                    return frozenset({'`NEVER`'})
            return frozenset(self.by_label(l) for l in label_sets)
        return frozenset(self.label_sets_to_nodes(ls) for ls in label_sets)

    def split_edgestr(self, edgestr, operator):
        questionable = False
        if edgestr.endswith('?'):
            edgestr = edgestr[:-1]
            questionable = True
        a, b = edgestr.split(operator)
        def handle_wildcard(n):
            if '*' not in n:
                if n in self.definitions:
                    definition = self.definitions[n]
                    if len(definition) != 1:
                        raise Exception(
                                f'{edgestr} contains incompatible definition.')
                    definition = list(definition)[0]
                    if len(definition) != 1:
                        raise Exception(
                                f'{edgestr} contains incompatible definition.')
                    n = list(definition)[0]
                result = self.by_label(n)
                if result is None:
                    return None
                return {result}
            if n.count('*') > 1:
                raise Exception(
                        f'{edgestr} contains multiple wildcard characters.')
            prefix, suffix = n.split('*')
            nodes = {n for n in self.nodes if n.label.startswith(prefix)
                     and n.label.endswith(suffix)}
            return nodes

        aa = handle_wildcard(a)
        bb = handle_wildcard(b)
        if aa is None or bb is None or not (aa and bb):
            raise Exception(f'{edgestr} contains unknown node.')
        return aa, bb, questionable

    def add_multiedge(self, edgestr, conditions=None):
        if conditions is None:
            conditions = {frozenset()}
        elif conditions:
            for condition in list(conditions):
                for c in condition:
                    if isinstance(c, str) and '`NEVER`' in c:
                        conditions.remove(condition)
                        break
            if not conditions:
                return
        assert len(conditions) >= 1
        assert '`NEVER`' not in str(conditions)

        for operator in ['=>', '>>', '=', '>']:
            if operator not in edgestr:
                continue
            aa, bb, questionable = self.split_edgestr(edgestr, operator)
            break
        else:
            raise Exception(f'Invalid multiedge: {edgestr}')

        for a in sorted(aa):
            for b in sorted(bb):
                if a is b:
                    continue
                if operator =='=>':
                    a.add_edges(b, conditions, questionable=questionable)
                    b.add_edges(a, conditions, questionable=questionable)
                    req = self.Requirement.from_line(
                            f'.bridge {b} {a}', self)
                elif operator == '>>':
                    edges = a.add_edges(b, conditions, questionable=True)
                    req = self.Requirement.from_line(
                            f'.require {a} {b}', self)
                elif operator == '=':
                    a.add_edges(b, conditions, questionable=questionable)
                    b.add_edges(a, conditions, questionable=questionable)
                elif operator == '>':
                    a.add_edges(b, conditions, questionable=questionable)
                else:
                    raise Exception(f'Unhandled operator ({operator}).')

        return (a, b)

    def rerank(self):
        for n in self.nodes:
            n.rank = None

        to_rank = self.reachable_from_root
        rank = 0
        self.root.rank = rank
        preranked = None
        ranked = set()
        rankable = {self.root}

        while True:
            rank += 1
            to_rank = (self.reachable_from_root & rankable) - ranked
            if not to_rank:
                break
            if ranked == preranked:
                for n in to_rank:
                    n.verify_required()
                if any(n.dependencies - ranked for n in to_rank):
                    raise DoorRouterException('Required nodes conflict.')
            assert ranked != preranked
            preranked = set(ranked)
            for n in to_rank:
                reverse_edges = {e for e in n.reverse_edges
                                 if e.source in preranked
                                 and e.true_condition <= preranked}
                if n is not self.root and not reverse_edges:
                    continue
                if n.dependencies - preranked:
                    continue
                for g in n.full_guaranteed:
                    preguaranteed = (n.guaranteed | g) - {n}
                    if preguaranteed <= preranked:
                        n.rank = rank
                        ranked.add(n)
                        for e in n.edges:
                            rankable.add(e.destination)
                        break

    def generate_reduced_edge_ranks(self):
        reduced_node_ranks = {}
        for n in self.nodes:
            rn = self.reduced_graph.node_mapping[n]
            rank = rn.rank
            if rank is None:
                rank = len(self.nodes) + 1
            reduced_node_ranks[n] = rank
        reduced_edge_ranks = {}
        for e in self.all_edges:
            nodes = {e.source, e.destination} | e.true_condition
            max_rank = max(reduced_node_ranks[n] for n in nodes)
            condition_rank = max(reduced_node_ranks[n]
                                 for n in e.true_condition | {self.root})
            reduced_edge_ranks[e] = (max_rank, condition_rank)
        self.reduced_edge_ranks = reduced_edge_ranks

    def reguarantee(self):
        assert hasattr(self, 'reduced_graph')
        assert self.reduced_graph is not None
        rgraph = self.reduced_graph
        root = self.root
        rroot = rgraph.root
        if not hasattr(self, 'reduced_edge_ranks'):
            self.generate_reduced_edge_ranks()
        for n in self.reachable_from_root:
            rn = self.reduced_graph.node_mapping[n]
            root.guar_to[n] = rgraph.remap_nodes(rroot.guar_to[rn])
            root.full_guar_to[n] = frozenset({
                    rgraph.remap_nodes(fg) for fg in rroot.full_guar_to[rn]})
            root.edge_guar_to[n] = {
                    e for (e, rank) in self.reduced_edge_ranks.items()
                    if rank[0] <= rn.rank}

        root.strict_full_guar_to = None
        root.guaranteed = frozenset({root})
        root.full_guaranteed = {root.guaranteed}
        root.edge_guar_to[root] = frozenset()

        _, x = root.get_guaranteed_reachable_only()
        self._edge_reachable_from_root = x
        valid_edges = {e for e in self.all_edges
                       if e.source.guaranteed is not None
                       and e.destination.guaranteed is not None
                       and self.reachable_from_root >= e.true_condition}
        if valid_edges != self._edge_reachable_from_root:
            assert valid_edges >= self._edge_reachable_from_root
            valid_edges = set(self._edge_reachable_from_root)
        self.root.propagate_guarantees(valid_edges, frozenset(valid_edges))
        assert len(self.root.guaranteed) <= 1

    def rerank_and_reguarantee(self):
        self.reguarantee()
        self.rerank()
        return

    def get_equivalence_groups(self):
        nodes = set(self.nodes)

        equivalence_groups = set()
        while nodes:
            n = nodes.pop()
            group = n.equivalent_nodes
            assert group <= nodes | {n}
            nodes -= group
            equivalence_groups.add(group)

        for g1 in equivalence_groups:
            for g2 in equivalence_groups:
                if g1 is g2:
                    continue
                assert not (g1 & g2)

        return equivalence_groups

    def get_reduced_graph(self, minimal=None):
        assert REDUCE
        if minimal is None:
            #minimal = hasattr(self, '_reachable_from_root') and \
            #        not self.parent
            minimal = False

        rng_state = random.getstate()

        egs = self.get_equivalence_groups()
        eg_nodes = {n for eg in egs for n in eg}
        g = Graph(parent=self, config=dict(self.config))
        g.node_mapping = {}
        leader_dict = {}
        sort_key = lambda n: (n.rank if n.rank is not None else -1, n)
        root = None
        done_labels = set()
        for eg in egs:
            if self.root in eg:
                group_leader = self.root
            else:
                temp = eg & self.conditional_nodes
                if temp:
                    group_leader = min(temp, key=sort_key)
                else:
                    group_leader = min(eg, key=sort_key)

            leader_dict[eg] = group_leader
            assert group_leader.label not in done_labels
            n = g.Node(group_leader.label, g)
            done_labels.add(group_leader.label)
            g.node_mapping[n] = eg
            for n2 in eg:
                g.node_mapping[n2] = n
            if group_leader is self.root:
                root = n
        assert root is not None
        g.set_root(root)

        g.edge_mapping = {}
        g.reverse_edge_mapping = defaultdict(set)
        for e in self.all_edges:
            if not ({e.source, e.destination} <= eg_nodes):
                continue
            if e.destination in e.source.equivalent_nodes:
                assert g.node_mapping[e.source] is \
                        g.node_mapping[e.destination]
                continue
            if not (e.combined_conditions < eg_nodes):
                continue
            a = leader_dict[e.source.equivalent_nodes]
            b = leader_dict[e.destination.equivalent_nodes]
            if e.combined_conditions:
                true_condition = {leader_dict[n.equivalent_nodes].label
                                  for n in e.true_condition}
                false_condition = {leader_dict[n.equivalent_nodes].label
                                   for n in e.false_condition}
                condition = true_condition | {f'!{c}' for c in false_condition}
                if condition:
                    condition = '&'.join(condition)
            else:
                condition = None
            new_edge = g.add_edge(a.label, b.label,
                                  condition=condition, simplify=True,
                                  update_caches=False,
                                  force_return_edges=True,
                                  questionable=e.questionable)
            assert len(new_edge) == 1
            new_edge = new_edge.pop()
            assert isinstance(new_edge, Graph.Node.Edge)
            g.edge_mapping[e] = new_edge
            g.reverse_edge_mapping[new_edge].add(e)

        for e in g.edge_mapping:
            e1 = g.edge_mapping[e]
            if e1 not in e1.source.edges:
                chosen = e1
                while True:
                    alternates = {e2 for e2 in e1.source.edges
                                  if e2.destination is e1.destination and
                                  e2.true_condition < chosen.true_condition}
                    if not alternates:
                        break
                    chosen = alternates.pop()
                assert chosen in e1.source.edges
                g.edge_mapping[e] = chosen

        for e1 in self.all_edges:
            if e1.false_condition:
                raise NotImplementedError
            source = g.node_mapping[e1.source]
            destination = g.node_mapping[e1.destination]
            condition = {g.node_mapping[n] for n in e1.true_condition}
            for e2 in g.reverse_edge_mapping:
                if not (e2.true_condition <= condition):
                    continue
                if e1.questionable != e2.questionable:
                    continue
                if e2.source is source and e2.destination is destination:
                    g.reverse_edge_mapping[e2].add(e1)
                    if e1 in g.edge_mapping:
                        assert g.edge_mapping[e1] is e2 or \
                                g.edge_mapping[e1].true_condition < condition
                    else:
                        g.edge_mapping[e1] = e2
                if source is not destination:
                    continue
                if e2.source is source or e2.destination is destination:
                    g.reverse_edge_mapping[e2].add(e1)

        g.clear_rooted_cache()
        assert not hasattr(g, '_reachable_from_root')

        if minimal:
            while True:
                g2 = g.get_reduced_graph(minimal=False)
                assert len(g2.nodes) <= len(g.nodes)
                assert len(g2.all_edges) <= len(g.all_edges)
                if len(g2.nodes) == len(g.nodes) and \
                        len(g2.all_edges) == len(g.all_edges):
                    break
                raise NotImplementedError('Need to update node mappings.')
                g = g2

        random.setstate(rng_state)
        return g

    def remap_nodes(self, nodes):
        if not nodes:
            return frozenset()
        if not hasattr(self, 'remapping_cache'):
            self.remapping_cache = {}
        if nodes in self.remapping_cache:
            return self.remapping_cache[nodes]
        parents = {n.parent is self for n in nodes}
        assert len(parents) == 1
        is_parent = parents.pop()
        self.remapping_cache[nodes] = \
                frozenset.union(*{self.node_mapping[n] for n in nodes})
        assert {n.parent is self != is_parent
                for n in self.remapping_cache[nodes]}
        return self.remap_nodes(nodes)

    def remap_edges(self, edges):
        if not isinstance(edges, frozenset):
            edges = frozenset(edges)
        if edges in self.remapping_cache:
            return self.remapping_cache[edges]
        result = frozenset({e2 for e1 in edges
                            for e2 in self.reverse_edge_mapping[e1]})
        self.remapping_cache[edges] = result
        return self.remap_edges(edges)

    def get_redundant_nodes(self):
        edges = []
        double_edges = []
        for n in self.nodes:
            if len(n.edges) >= 3 or len(n.reverse_edges) >= 3:
                continue
            if len(n.edges) != len(n.reverse_edges):
                continue
            if not (n.edges or n.reverse_edges):
                continue
            if len(n.edges) == 1:
                if list(n.edges)[0].destination is \
                        list(n.reverse_edges)[0].source:
                    continue
                edges.append((list(n.reverse_edges)[0], list(n.edges)[0]))
                continue
            for e in n.edges:
                if e.pair not in n.reverse_edges:
                    break
            else:
                assert len(n.edges) == len(n.reverse_edges) == 2
                a, b = sorted(n.edges)
                double_edges.append((b.pair, a))
                double_edges.append((a.pair, b))
        return double_edges + edges

    def get_no_return_nodes(self, allow_nodes):
        no_returns = set()
        nodes = sorted(self.reachable_from_root-self.root_reachable_from,
                       key=lambda n: (n.rank, n))
        if not nodes:
            return no_returns

        allow_nodes = set(allow_nodes | self.root_reachable_from)
        for n in reversed(sorted(nodes, key=lambda x: (x.rank, x))):
            rfn, _, _ = n.get_guaranteed_reachable(
                    strict=True, seek_nodes=allow_nodes)
            others = rfn & allow_nodes
            if rfn & self.root_reachable_from:
                # This is because our "root_reachable_from" doesn't always
                # capture every correct node
                allow_nodes = allow_nodes | {n} | self.root_reachable_from
                continue
            if not others:
                raise DoorRouterException(
                        f'Unable to fix no return situation: {n}.')
            assert n in rfn
            allow_nodes.add(n)
            no_returns |= rfn
        return no_returns

    def get_add_edge_options(self):
        options = []
        for o in sorted(self.unconnected):
            if not o.rooted:
                continue
            if o.dependencies <= self.rooted:
                options.append(o)
        if not options:
            raise DoorRouterException('No connectable options.')
        return frozenset(options)

    def commit(self, version=None):
        super().commit(version)
        for n in self.nodes:
            n.commit(version)
        self.changelog.append(('COMMIT', version))

    def rollback(self, version=None):
        super().rollback(version)
        for n in self.nodes:
            n.rollback(version)
        self.changelog.append(('ROLLBACK', version))

    def get_pretty_changelog(self):
        s = ''
        for i, (command, parameter) in enumerate(self.changelog):
            if isinstance(parameter, Graph.Node.Edge):
                parameter = str(parameter).strip('*')
            if parameter is None:
                s += f'{i:0>4} {command}\n'
            else:
                s += f'{i:0>4} {command} {parameter}\n'
        return s.strip()

    def dump(self, outfile=None):
        if outfile is not None:
            outfile = open(outfile, 'w+')

        def linedump(msg):
            msg = f'DUMP {self.seed} {self.num_loops} {msg}'
            if outfile is not None:
                outfile.write(msg + '\n')
            else:
                print(msg)

        def dumpsort(xs):
            if not xs:
                return xs
            test = list(xs)[0]
            try:
                test = list(xs)
                return sorted(xs, key=lambda x: dumpstr(x))
            except TypeError:
                return sorted(xs, key=lambda x: str(x))

        def dumpstr(xs):
            return ';'.join(sorted(str(x) for x in xs))

        for e in dumpsort(self.all_edges):
            linedump(e)

        for n in dumpsort(self.reachable_from_root):
            linedump(f'{n} R {n.rank}')
            linedump(f'{n} G {dumpstr(n.guaranteed)}')
            if hasattr(n, 'prereachable'):
                for key in n.prereachable:
                    linedump(f'{n} PRE {key} N '
                             f'{dumpstr(n.prereachable[key][0])}')
                    linedump(f'{n} PRE {key} E '
                             f'{dumpstr(n.prereachable[key][1])}')
            if hasattr(n, 'prereachable_from'):
                linedump(f'{n} PREFROM {dumpstr(n.prereachable_from)}')
            for fg in dumpsort(n.full_guaranteed):
                linedump(f'{n} FG {dumpstr(fg)}')
            for attr in ['guar_to', 'edge_guar_to']:
                if not hasattr(n, attr):
                    continue
                datadict = getattr(n, attr)
                for n2 in dumpsort(datadict):
                    linedump(f'{n} {attr} {n2} {dumpstr(datadict[n2])}')
            for attr in ['full_guar_to', 'strict_full_guar_to']:
                if not hasattr(n, attr):
                    continue
                datadict = getattr(n, attr)
                if datadict is None:
                    continue
                for n2 in dumpsort(datadict):
                    for fg in dumpsort(datadict[n2]):
                        linedump(f'{n} {attr} {n2} {dumpstr(fg)}')

        if outfile is not None:
            outfile.close()

    def check_theoretically_reachable(self, nodeset, partial=False):
        if not hasattr(self, 'theoretically_reachable'):
            return True
        if partial and nodeset & self.theoretically_reachable:
            return True
        if nodeset <= self.theoretically_reachable:
            return True
        raise DoorRouterException(f'{nodeset} is IMPOSSIBLE to reach.')

    def verify_no_return(self):
        if not self.config['avoid_softlocks']:
            return
        if self.num_loops < 0:
            return
        if self.goal_reached and \
                self.reachable_from_root <= self.root_reachable_from:
            return
        self.get_no_return_nodes(allow_nodes=self.get_add_edge_options())

    def verify_goal(self):
        if self.reachable_from_root - self.root_reachable_from:
            raise DoorRouterException(
                    'Graph contains points of no return.')
        for n in self.goal_nodes:
            if not n.rooted:
                raise DoorRouterException(
                    f'Unrooted goal node {n}.')
        return True

    def verify_edges(self):
        for e in self.all_edges:
            assert e in e.source.edges
            assert e in e.destination.reverse_edges
        for n in sorted(self.nodes):
            for e in n.edges:
                assert e in self.all_edges
            for e in n.reverse_edges:
                assert e in self.all_edges

    def verify_frozensets(self):
        for n1 in self.nodes:
            for attr in ['guar_to', 'full_guar_to',
                         'strict_full_guar_to', 'edge_guar_to']:
                if not hasattr(n1, attr):
                    continue
                datadict = getattr(n1, attr)
                if n1 is self.root and 'strict' in attr:
                    assert datadict is None
                    continue
                for n2 in datadict:
                    assert isinstance(datadict[n2], frozenset)

    def verify_guar_to(self):
        for n1 in self.nodes:
            if n1.guaranteed:
                assert n1.guaranteed == self.expand_guaranteed(n1.guaranteed)
            if n1.guar_to and n1.guaranteed:
                assert n1.guar_to[n1] == n1.guaranteed
        assert self.root.strict_full_guar_to is None

    def verify(self):
        self.rooted
        if self.config['no_logic']:
            return
        if DEBUG:
            self.verify_edges()
            self.verify_frozensets()
            self.verify_guar_to()
        for req in self.requirements:
            if hasattr(req, 'joiner') and req.joiner:
                continue
            req.verify()
        self.verify_no_return()

    def verify_goal_connectable(self):
        assert self.connectable and self.root in self.connectable
        satisfaction = set(self.allow_connecting)
        while True:
            old = set(satisfaction)
            for n in old:
                for e in n.edges:
                    if e.destination in self.connectable:
                        continue
                    if e.true_condition <= satisfaction:
                        satisfaction.add(e.destination)
            if satisfaction == old:
                break
        for g in self.goal_nodes:
            reachable_from = {g}
            while True:
                updated = False
                if reachable_from & (self.unconnected | {self.root}):
                    node_passed = True
                    break
                for n in set(reachable_from):
                    for e in n.reverse_edges:
                        if e.true_condition <= satisfaction:
                            if e.source not in reachable_from:
                                reachable_from.add(e.source)
                                updated = True
                if not updated:
                    raise Exception(f'Cannot connect required node {g}.')

    def add_edge(self, a, b, condition=None, procedural=False,
                 directed=True, simplify=False, update_caches=True,
                 force_return_edges=False, questionable=False):
        if isinstance(a, str):
            a = self.get_by_label(a)
        if isinstance(b, str):
            b = self.get_by_label(b)
        if not condition:
            conditions = {frozenset()}
        elif isinstance(condition, frozenset):
            conditions = {condition}
        elif isinstance(condition, set):
            conditions = condition
        else:
            conditions = self.expand_labels(condition)
        edges = set()
        edges |= a.add_edges(b, conditions, procedural=procedural,
                             simplify=simplify, update_caches=update_caches,
                             force_return_edges=force_return_edges,
                             questionable=questionable)
        if not directed:
            edges |= b.add_edges(
                    a, conditions, procedural=procedural,
                    simplify=simplify, update_caches=update_caches,
                    force_return_edges=force_return_edges,
                    questionable=questionable)
        if force_return_edges:
            assert edges
        return edges

    def procedural_add_edge(self, strict_candidates, lenient_candidates):
        options = self.get_add_edge_options()

        dependency_options = {o for o in options if o.dependencies}
        bad_dependency_options = {o for o in dependency_options
                                  if not o.dependencies & self.rooted}
        options -= bad_dependency_options
        if not (options or self.config['no_logic']):
            raise DoorRouterException('No connectable options.')

        # filter by tags
        compatibility_dict = {}
        for o in options:
            others = set(n for n in self.unconnected
                         if o.check_tag_compatibility(n)) - {o}
            compatibility_dict[o] = others
        temp = [o for o in options if compatibility_dict[o]]
        if temp:
            options = temp

        options = sorted(options, key=lambda o: (
            len(self.discourage_nodes[o]), o.random_sort_key, o))
        a = random.choice(options)
        others = compatibility_dict[a]
        others.discard(a)
        old_others = set(others)

        # filter by guarantee
        required_guarantee = set()
        required_bridges = set()
        for n in a.free_travel_nodes:
            if n.required_guarantee:
                required_guarantee |= n.required_guarantee
            if n.required_bridges:
                required_bridges |= n.required_bridges

        if required_guarantee:
            x = {o for o in others if not o.rooted}
            y = {o for o in others
                 if o.rooted and o.guaranteed | {a} >= required_guarantee}
            others = x | y

        if required_bridges:
            x = {o for o in others if not o.rooted}
            y = {o for o in others
                 if o.rooted and o.guaranteed_edges & required_bridges}
            others = x | y

        bad_guarantee = set()
        good_guarantee = set()
        for o1 in others:
            if o1 in bad_guarantee | good_guarantee:
                continue
            required_guarantee = set()
            required_bridges = set()
            for o2 in o1.free_travel_nodes:
                if o2.required_guarantee:
                    required_guarantee |= o2.required_guarantee
                if o2.required_bridges:
                    required_bridges |= o2.required_bridges
            if required_guarantee - (a.guaranteed | {o1}):
                bad_guarantee |= o1.free_travel_nodes
                assert o1 in bad_guarantee
            if required_bridges and \
                    not (required_bridges & a.guaranteed_edges):
                bad_guarantee |= o1.free_travel_nodes
                assert o1 in bad_guarantee
            if o1 not in bad_guarantee:
                good_guarantee |= o1.free_travel_nodes
        assert not good_guarantee & bad_guarantee
        assert good_guarantee | bad_guarantee >= others
        others -= bad_guarantee
        self.discourage_nodes[a] |= (old_others - others)
        for o in old_others - others:
            self.discourage_nodes[o].add(a)

        if self.config['no_logic']:
            others = old_others

        if a in strict_candidates:
            others &= strict_candidates[a]

        old_others = set(others)

        if not others:
            raise DoorRouterException(f'Node {a} has no connectable options.')

        temp = others - self.discourage_nodes[a]
        if temp:
            others = temp
        else:
            self.discourage_nodes[a] = set()

        if a in lenient_candidates:
            temp = others & lenient_candidates[a]
            if temp:
                others = temp

        if len(self.reachable_from_root & self.unconnected) <= 2 and \
                not self.goal_reached:
            assert a in self.reachable_from_root & self.unconnected
            want_edges = {e for e in self.all_edges
                          if e.source.rooted and not e.destination.rooted}
            want_nodes = {n for e in want_edges for n in e.true_condition}
            want_nodes |= (self.goal_nodes - self.reachable_from_root)
            temp = set()
            for o in others - self.reachable_from_root:
                connected = o.connected_nodes
                degree = len((connected & self.unconnected)
                             - self.reachable_from_root)
                if degree >= 2:
                    temp.add(o)
                elif connected & want_nodes:
                    temp.add(o)
                    if connected & (want_nodes-self.goal_nodes):
                        import pdb; pdb.set_trace()
            others = temp

        if self.config['no_logic']:
            others = old_others

        if self.previous_procedural_add_edge and \
                a in self.previous_procedural_add_edge:
            others -= self.previous_procedural_add_edge

        if others:
            others = sorted(others, key=lambda o: (
                len(self.discourage_nodes[o]), o.random_sort_key, o))
            max_index = len(others)-1
            index = random.randint(random.randint(0, max_index), max_index)
            b = others[index]
        else:
            raise DoorRouterException(f'Node {a} has no connectable options.')

        assert {a, b} != self.previous_procedural_add_edge
        self.add_edge(a, b, directed=False, procedural=True, simplify=False)
        self.discourage_nodes[a].add(b)
        self.discourage_nodes[b].add(a)
        self.unconnected -= {a, b}
        log(f'ADD {a} {b}')
        self.previous_procedural_add_edge = {a, b}
        return self.previous_procedural_add_edge

    def procedural_remove_edge(self):
        all_edges = {e for e in self.all_edges if e.generated}
        temp = all_edges - self.discourage_edges
        if temp:
            all_edges = temp
        else:
            self.discourage_edges = set()

        assert all_edges
        all_edges = sorted(all_edges)
        random.shuffle(all_edges)
        for e in all_edges:
            if not e.check_is_bridge():
                break
        self.discourage_edges.add(e)
        self.discourage_edges.add(e.pair)
        a, b = e.source, e.destination
        self.discourage_nodes[a].add(b)
        self.discourage_nodes[b].add(a)
        assert not self.unconnected & {a, b}
        old_rooted = self.rooted
        e.bidirectional_remove()
        self.unconnected |= {a, b}
        log(f'REMOVE {a} {b}')
        self.previous_procedural_add_edge = None

    def generate_solutions(self, goal_nodes=None):
        print('Generating solution paths...')
        if not goal_nodes:
            goal_nodes = set(self.goal_nodes)
        expanded = self.expand_guaranteed(goal_nodes)
        goal_nodes |= expanded & self.conditional_nodes

        avoid_edges = {e for e in self.all_edges
                       if e.destination in e.source.dependencies}

        paths = {}
        ignore_nodes = set()
        while True:
            for n in sorted(goal_nodes-ignore_nodes, key=lambda n: n.rank):
                if n in paths:
                    continue
                avoid_nodes = frozenset({a for a in self.nodes if
                                         a.rank is not None and
                                         a.rank >= n.rank} - {n})
                paths[n] = n.get_shortest_path(avoid_nodes=avoid_nodes,
                                               avoid_edges=avoid_edges)
                if paths[n] is None:
                    paths[n] = n.get_shortest_path(avoid_nodes=None,
                                                   avoid_edges=avoid_edges)
                assert self.config['no_logic'] or paths[n] is not None
                if paths[n] is None:
                    ignore_nodes.add(n)
                    continue
                for e in paths[n]:
                    for c in e.true_condition:
                        goal_nodes.add(c)
            if goal_nodes == set(paths.keys()):
                break

        abridged_paths = []
        seen_edges = set()
        for n in sorted(goal_nodes-ignore_nodes, key=lambda n: (n.rank, n)):
            if n is self.root:
                continue
            path = paths[n]
            seen_path = [p for p in path if p in seen_edges]
            if seen_path:
                start = seen_path[-1]
            else:
                start = path[0]
                assert start.source is self.root
            assert path.count(start) == 1
            assert len(path) == len(set(path))
            path = path[path.index(start):]
            seen_edges |= set(path)
            abridged_paths.append((n, path))

        self.solutions = abridged_paths
        return self.solutions

    def visualize(self, output='visualize.html', relabel=None,
                  ignore_edges=None,
                  annotate_guaranteed=False, annotate_full_guaranteed=False,
                  annotate_edges=False,
                  height=720, width=1280,
                  rooted_only=True, physics=True):
        from pyvis.network import Network
        from math import sin, cos, pi
        import networkx
        import colorsys
        import json
        if relabel is None:
            relabel = {}
        if ignore_edges is None:
            ignore_edges = set()

        rooted_nodes = sorted(self.rooted, key=lambda n: (n.rank, n.label))
        unrooted_nodes = sorted(self.nodes-self.rooted,
                                key=lambda n: (n.label))
        if not rooted_only:
            nodes = rooted_nodes + unrooted_nodes
        else:
            nodes = rooted_nodes
        if rooted_nodes:
            max_rank = max(n.rank for n in rooted_nodes) + 1
        else:
            max_rank = -1

        edges = {e for e in self.all_edges
                 if {e.source, e.destination} <= set(nodes)}

        special_nodes = {self.root}
        if hasattr(self, 'goal'):
            special_nodes |= self.goal_nodes
        for e in edges:
            special_nodes |= e.true_condition
        special_nodes = {relabel[s.label] if s.label in relabel else s.label
                         for s in special_nodes}

        nxgraph = networkx.DiGraph()

        bigfont, midfont, smallfont = 18, 15, 12

        done_node_labels = set()
        coords = {}
        for i, n in enumerate(nodes):
            if max_rank > 1 and n.rank is not None:
                rank_ratio = (n.rank-1) / (max_rank-1)
            else:
                #rank_ratio = random.random()
                rank_ratio = 1
            hue = rank_ratio * (5/6)
            r, g, b = colorsys.hls_to_rgb(hue, 0.75, 1)
            r = int(round(r*255))
            g = int(round(g*255))
            b = int(round(b*255))
            color = f'#{r:0>2x}{g:0>2x}{b:0>2x}'
            if n.label in relabel:
                pretty_label = relabel[n.label]
            else:
                pretty_label = n.label
            if pretty_label in done_node_labels:
                continue
            done_node_labels.add(pretty_label)
            shape = 'ellipse'
            if n.rank is not None:
                sinval = sin(rank_ratio * 2 * pi)
                cosval = cos(rank_ratio * 2 * pi)
                x = int(round((width / 2) + (sinval * (width / 4))))
                y = -1 * int(round((height / 2) + (cosval * (height / 4))))
            else:
                x = int(round(width))
                y = int(round(height / 2)) + (height // 4)
            assert n.label not in coords
            coords[pretty_label] = (x, y)
            display_label = f'{pretty_label}'
            if pretty_label in special_nodes:
                display_label = display_label.split('\n')
                display_label[0] = f'<b>{display_label[0]}</b>'
                display_label = '\n'.join(display_label)
            if annotate_guaranteed:
                guaranteed = ','.join(sorted(g.label for g in n.guaranteed
                                             if g not in {n, self.root}))
                if guaranteed:
                    display_label += f'\n[{guaranteed}]'
            if annotate_full_guaranteed:
                fgs = {fg - n.guaranteed for fg in n.full_guaranteed}
                for i, fg in enumerate(sorted(
                        fgs, key=lambda ffgg: (len(ffgg), ffgg))):
                    if len(fgs) <= 1:
                        break
                    guaranteed = ','.join(sorted(g.label for g in fg))
                    if not guaranteed:
                        guaranteed = ' '
                    display_label += f'\n{i+1}. [{guaranteed}]'
            if annotate_edges:
                to_annotate = sorted(n.guaranteed_edges)
                s = '\n'.join([f'{e}' for e in to_annotate])
                display_label += f'\n{s}'
            if '\n' not in display_label:
                display_label = f' {display_label} '
            if pretty_label in special_nodes:
                nxgraph.add_node(
                    pretty_label, label=display_label, x=x, y=y,
                    color=color, shape=shape, font={'size': bigfont,
                                                    'multi': 'html'})
            else:
                nxgraph.add_node(pretty_label, label=display_label, x=x, y=y,
                                 color=color, shape=shape,
                                 font={'size': midfont})

        ranked_edges = {e for e in edges if e.source.rank is not None
                        and e.destination.rank is not None}
        unranked_edges = edges - ranked_edges
        ranked_edges = sorted(ranked_edges, key=lambda e: (
            e.destination.rank, e.source.rank, str(e)))
        unranked_edges = sorted(unranked_edges, key=lambda e: str(e))
        edges = ranked_edges + unranked_edges
        done_edges = set()
        done_edge_signatures = set()

        font = {'size': smallfont}
        for e in edges:
            if e in ignore_edges:
                continue
            source_label = e.source.label
            destination_label = e.destination.label
            if e.source.label in relabel:
                source_label = relabel[e.source.label]
            if e.destination.label in relabel:
                destination_label = relabel[e.destination.label]
            if source_label == destination_label:
                continue
            condition_labels = [
                relabel[n.label] if n.label in relabel else n.label
                for n in e.true_condition]
            if any('\n' in label for label in condition_labels):
                condition_label = '\n&\n'.join(sorted(condition_labels))
            else:
                condition_label = ' & '.join(sorted(condition_labels))
            key = (source_label, destination_label, condition_label)
            if key in done_edges:
                continue
            done_edges.add(key)
            if e.true_condition:
                edge_signature = str(e)
                assert edge_signature not in done_edge_signatures
                x1, y1 = coords[source_label]
                x2, y2 = coords[destination_label]
                x = (x1 + x2) >> 1
                y = (y1 + y2) >> 1
                nxgraph.add_node(edge_signature, label=f' {condition_label} ',
                                 color='#ffffff', shape='box', font=font,
                                 x=x, y=y)
                nxgraph.add_edge(source_label, edge_signature)
                source_node = [n for n in nxgraph.nodes
                               if str(n) == source_label]
                assert len(source_node) == 1
                nxgraph.add_edge(edge_signature, destination_label,
                                 color=nxgraph.nodes[source_label]['color'])
                done_edge_signatures.add(edge_signature)
            else:
                nxgraph.add_edge(source_label, destination_label)

        net = Network(height=f'{height}px', width=f'{width}px',
                      bgcolor='#000000', directed=True)
        net.inherit_edge_colors(True)
        net.from_nx(nxgraph)
        net.toggle_physics(physics)
        net.show_buttons()
        net.barnes_hut(gravity=-500, central_gravity=0.5, spring_length=40,
                       spring_strength=0.04, damping=0.9, overlap=0.95)
        net.write_html(output, notebook=False)

    def connect_everything(self):
        PROGRESS_BAR_LENGTH = 80
        PROGRESS_BAR_INTERVAL = (self.config['retry_limit_close'] /
                                 PROGRESS_BAR_LENGTH)

        strict_candidates = defaultdict(set)
        lenient_candidates = defaultdict(set)
        if self.strict_validator:
            for n1 in self.unconnected:
                for n2 in self.unconnected:
                    if n1 <= n2 and self.strict_validator(n1, n2):
                        strict_candidates[n1].add(n2)
                        strict_candidates[n2].add(n1)

        if self.lenient_validator:
            for n1 in self.unconnected:
                for n2 in self.unconnected:
                    if n1 <= n2 and self.lenient_validator(n1, n2):
                        lenient_candidates[n1].add(n2)
                        lenient_candidates[n2].add(n1)
            for n in self.unconnected:
                if n in strict_candidates and strict_candidates[n]:
                    lenient_candidates[n] = (lenient_candidates[n] &
                                             strict_candidates[n])

        self.discourage_nodes = defaultdict(set)
        self.discourage_edges = set()
        self.previous_procedural_add_edge = None

        self.verify_goal_connectable()

        failures = 0
        start_time = time()
        initial_unconnected = set(self.unconnected)
        self.num_loops = 0
        previous_progress_bar = 0
        t1 = time()
        while True:
            self.num_loops += 1
            random.seed(f'{self.seed}-{self.num_loops}')
            t3 = time()

            goal_reached = self.goal_reached
            if goal_reached:
                try:
                    self.verify_goal()
                    assert self.root_reachable_from >= self.reachable_from_root
                    break
                except DoorRouterException:
                    pass

            if self.num_loops % 5 == 0:
                if self.num_loops < 500:
                    stdout.write(f' {self.num_loops//5:>2}')
                    if self.num_loops % 100 == 0:
                        stdout.write('\n')
                else:
                    stdout.write(f' {self.num_loops//5:>3}')
                    if self.num_loops % 50 == 0:
                        stdout.write('\n')
                stdout.flush()

            t2 = time()
            time_limit = self.config['time_limit']
            if t2 - t1 > time_limit:
                raise DoorRouterException(
                    f'Failed to build maze within {time_limit} seconds.\n'
                    f'Number of operations: {self.num_loops-1}')

            if self.num_loops > self.config['retry_limit_close'] or (
                    self.num_loops > self.config['retry_limit']
                    and not goal_reached):
                raise DoorRouterException(
                    f'Failed to build maze within {self.num_loops-1} '
                    f'operations.\nTime taken: {round(t2-t1,1)} seconds.')
            backup_unconnected = set(self.unconnected)

            if DEBUG:
                self.reachable_from_root
                self.verify()

            try:
                add_edge = False
                remove_edge = False
                if self.unconnected:
                    assert self.unconnected & self.rooted
                    if failures <= 1:
                        add_edge = True
                    elif len(self.initial_unconnected) == \
                            len(self.unconnected):
                        add_edge = True
                    elif random.random() < ((1/failures)**0.25):
                        add_edge = True
                    else:
                        add_edge = False

                if add_edge:
                    self.procedural_add_edge(strict_candidates,
                                             lenient_candidates)
                else:
                    remove_edge = True

                if remove_edge:
                    self.procedural_remove_edge()
                    failures = 0

                if goal_reached and not self.goal_reached:
                    raise DoorRouterException(
                            f'Action would undo victory condition.')

                if not (self.goal_reached or
                        self.reachable_from_root & self.unconnected):
                    raise DoorRouterException(f'Orphaned root cluster.')

                self.verify()
                self.commit()
                failures = 0
                unrootable = self.rooted - self.root_reachable_from
                report = f'{len(self.unconnected)}/' \
                        f'{len(unrootable)} {self.goal_reached}'

            except DoorRouterException as error:
                self.unconnected = backup_unconnected
                self.rollback()
                unrootable = self.rooted - self.root_reachable_from
                report = f'{len(self.unconnected)}/' \
                        f'{len(unrootable)} {self.goal_reached}'
                report = f'{report} {error}'
                if DEBUG:
                    self.reachable_from_root
                    self.verify()
                failures += 1

            t4 = time()
            duration = int(round((t4-t3)*1000))
            report = f'{self.num_loops} {duration:>6}ms {report}'
            log(report)

        print()

    def build_graph(self):
        attempts = 0
        while True:
            attempts += 1
            self.attempts = attempts
            print(f'Maze generation attempt #{attempts}, seed {self.seed}...')
            print(f'Connecting {len(self.initial_unconnected)} nodes.')
            try:
                t1 = time()
                self.connect_everything()
                t2 = time()
                print(f'Completed maze on attempt #{attempts} after '
                      f'{self.num_loops} operations and {round(t2-t1,1)} '
                      f'seconds.')
                break
            except DoorRouterException as error:
                print()
                print(f'ERROR: {error}')
                if DEBUG:
                    print(self.description_problematic)
                sleep(1)
                self.reinitialize()

DoorRouter = Graph
