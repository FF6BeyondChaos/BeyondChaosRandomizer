from .utils import cached_property, utilrandom as random
from collections import defaultdict
from itertools import product
from sys import stdout
from hashlib import md5


class ItemRouterException(Exception):
    pass


class ItemRouter:
    def __init__(self, requirefile, restrictfile=None, linearity=0.8):
        self.definitions = set([])
        self.restrictions = {}
        self.assign_conditions = {}
        self.assignments = {}
        self.linearity = linearity

        self.routeseed = random.randint(0, 9999999999)

        f = open(requirefile)
        for line in f.readlines():
            line = line.strip()
            if not line or line[0] == '#':
                continue
            while '  ' in line:
                line = line.replace('  ', ' ')

            if line.startswith(".def "):
                line = line[5:]
                definition = True
            else:
                assert not line.startswith('.')
                definition = False

            try:
                label, reqs = line.split(' ', 1)
            except ValueError:
                continue

            if definition:
                self.definitions.add(label)
                assert label not in self.assign_conditions
            self.assign_conditions[label] = reqs

        f.close()

        if restrictfile is not None:
            restrictdefs = {}
            f = open(restrictfile)
            for line in f.readlines():
                line = line.strip()
                if not line or line[0] == '#':
                    continue
                while '  ' in line:
                    line = line.replace('  ', ' ')

                if line.startswith(".def "):
                    line = line[5:]
                    label, value = line.split()
                    restrictdefs[label] = value
                else:
                    assert not line.startswith('.')
                    location, values = line.split()
                    values = values.split(',')
                    while True:
                        newvalues = [
                            restrictdefs[v] if v in restrictdefs else v
                            for v in values]
                        if newvalues == values:
                            break
                        values = (','.join(newvalues)).split(',')
                    assert location not in self.restrictions
                    self.restrictions[location] = set(values)

    @property
    def report(self):
        locations = sorted(self.assignments,
                           key=lambda l: self.get_location_rank(l))
        maxlen = max(len(l) for l in locations)
        s = ""
        for l in locations:
            item = self.assignments[l]
            name = self.get_best_definition_by_requirement(item)
            if name is None:
                name = item
            else:
                name = "{0} {1}".format(item, name)
            s += ("{0:%s}: {1}\n" % maxlen).format(l, name)
        return s.strip()

    @cached_property
    def all_locations(self):
        locations = set([k for k in self.assign_conditions if
                         k not in self.definitions])
        return locations

    @property
    def assigned_locations(self):
        return set(self.assignments.keys())

    @property
    def assigned_items(self):
        return set(self.assignments.values())

    @property
    def unassigned_locations(self):
        return self.all_locations - self.assigned_locations

    @property
    def assignable_locations(self):
        if not hasattr(self, "_assignable_locations_previous_assigned"):
            self._assignable_locations_previous_assigned = None
        if (self._assignable_locations_previous_assigned
                != self.assigned_locations):
            setattr(self, "_assignable_locations_previous_assigned",
                    self.assigned_locations)
            self._assignable_locations = None
        if self._assignable_locations is not None:
            return self._assignable_locations
        assignable = set([k for k in self.unassigned_locations if
                          self.check_assignable(k)])
        self._assignable_locations = assignable
        return self.assignable_locations

    @property
    def unreachable_locations(self):
        return set([
            k for k in self.all_locations if
            k not in self.assignable_locations and
            k not in self.assigned_locations])

    @property
    def ranked_requirements(self):
        requirements = set([r for label in self.assign_conditions for r in
                            self.get_simplified_requirements(label)])
        unreachables = self.unreachable_locations
        counts = {}
        counts = [(len([u for u in unreachables
                        if req in self.get_simplified_requirements(u)]),
                   random.random(), req)
                  for req in requirements]
        return [req for (count, _, req) in sorted(counts)
                if count > 0 and req not in self.assigned_items]

    @property
    def unassigned_items(self):
        return self.ranked_requirements

    @cached_property
    def requirements_locations(self):
        d = defaultdict(set)
        for label in self.all_locations:
            for req in self.get_simplified_requirements(label):
                if req is None:
                    continue
                req = tuple(sorted(req))
                d[req].add(label)
        return d

    @property
    def unassigned_custom_assignments(self):
        return sorted([(k, v) for (k, v) in self.custom_assignments.items()
                       if k not in self.assignments])

    def rankrand(self, thing):
        return md5(str(thing) + str(self.routeseed)).hexdigest()

    def get_simplified_requirements(self, label, parent_labels=None,
                                    force=False):
        if not hasattr(self, "_previous_simplified"):
            self._previous_simplified = {}
        if label in self._previous_simplified and not force:
            return self._previous_simplified[label]

        if parent_labels is None:
            parent_labels = []
        if parent_labels.count(label) > 5:
            return None
        parent_labels.append(label)

        conditions = self.assign_conditions[label]
        if conditions == '*':
            return set([])
        requirements = set([])
        for or_cond in conditions.split('|'):
            subreqs = []
            for and_cond in or_cond.split('&'):
                if and_cond in self.definitions:
                    subreqs.append(
                        self.get_simplified_requirements(
                            and_cond, parent_labels=parent_labels))
                else:
                    subreqs.append(set([frozenset([and_cond])]))
                if None in subreqs:
                    break
            if None in subreqs:
                requirements.add(None)
                continue

            if len(subreqs) >= 1 and all(reqs == set([]) for reqs in subreqs):
                requirements = set([])
                self._previous_simplified[label] = requirements
                return self.get_simplified_requirements(label)

            subreqs = [s for s in subreqs if s]
            for permutation in sorted(product(*subreqs)):
                if None in permutation:
                    requirements.add(None)
                    continue
                newsubreqs = set([])
                for p in permutation:
                    newsubreqs |= p
                assert all([isinstance(n, str) for n in newsubreqs])
                requirements.add(frozenset(newsubreqs))

        if None in requirements and requirements == {None}:
            stdout.write('.')
            self._previous_simplified[label] = requirements
            return self.get_simplified_requirements(label)

        requirements = set([r for r in requirements if r])
        for r1 in sorted(requirements):
            for r2 in sorted(requirements):
                if r1 < r2 and r2 in requirements:
                    requirements.remove(r2)

        assert isinstance(requirements, set)
        assert all([isinstance(r, frozenset) for r in requirements])
        self._previous_simplified[label] = requirements
        return self.get_simplified_requirements(label)

    def get_best_definition_by_requirement(self, req):
        ranker = lambda d: (
            max(len(reqs) for reqs in
                self.get_simplified_requirements(d) | set([])), d)
        candidates = [d for d in self.definitions
                      if any(req in reqs for reqs in
                             self.get_simplified_requirements(d))]
        if not candidates:
            return None
        temp = [c for c in candidates if req in self.assign_conditions[c]]
        candidates = temp or candidates
        temp = [c for c in candidates if req == self.assign_conditions[c]]
        candidates = temp or candidates
        return sorted(candidates, key=ranker)[0]

    def check_assignable(self, label):
        if not hasattr(self, "_check_assignable_previous_items"):
            self._check_assignable_previous_items = None
        if self.assigned_items != self._check_assignable_previous_items:
            self._check_assignable_previous_items = self.assigned_items
            self._check_assignable_cache = {}
        if label in self._check_assignable_cache:
            return self._check_assignable_cache[label]
        requirements = self.get_simplified_requirements(label)
        if requirements == {None}:
            return False

        result = False
        if not requirements:
            result = True
        else:
            for and_reqs in requirements:
                for r in and_reqs:
                    if r not in self.assigned_items:
                        break
                else:
                    result = True

        self._check_assignable_cache[label] = result
        return self.check_assignable(label)

    def get_assigned_location(self, item):
        for key, value in self.assignments.items():
            if value == item:
                return key
        return None

    def get_item_unlocked_locations(self, items):
        if isinstance(items, str):
            items = [items]
        baseline_locations = self.assignable_locations
        for item in items:
            key = "_temp_%s" % item
            self.assignments[key] = item
        unlocked_locations = self.assignable_locations - baseline_locations
        for item in items:
            key = "_temp_%s" % item
            del(self.assignments[key])
        return unlocked_locations

    def get_location_rank(self, location):
        for i in sorted(self.location_ranks):
            if location in self.location_ranks[i]:
                return i
        return None

    def get_complexity_rank(self, location):
        if not self.get_simplified_requirements(location):
            return 0
        a_value = min([len(reqs) for reqs in
                       self.get_simplified_requirements(location)])
        b_value = min([len(reqs | self.assigned_items)
                       / float(len(reqs & self.assigned_items)+1)
                       for reqs in self.get_simplified_requirements(location)])
        return a_value, b_value

    def sort_by_item_usage(self, locations):
        fail_counter = defaultdict(int)
        for item in self.assigned_items:
            remember_location = self.get_assigned_location(item)
            del(self.assignments[remember_location])
            assignable_locations = self.assignable_locations
            for l in locations:
                if l not in assignable_locations:
                    fail_counter[l] += 1
            self.assignments[remember_location] = item
        locations = sorted(sorted(locations),
                           key=lambda l: (fail_counter[l],
                                          self.get_location_rank(l),
                                          random.random()))
        return locations

    def get_valid_locations(self, req, include_unreachable=False):
        if include_unreachable:
            candidates = self.all_locations
        else:
            candidates = self.assignable_locations
        for location, item in self.custom_assignments.items():
            if item != req:
                candidates = [c for c in candidates if c != location]
        valids = set([])
        for c in candidates:
            if c not in self.restrictions:
                valids.add(c)
            elif req in self.restrictions[c]:
                valids.add(c)
        return valids

    def set_custom_assignments(self, custom_assignments):
        self.custom_assignments = dict(custom_assignments)

    def force_custom(self):
        for l, item in self.custom_assignments.items():
            if l in self.assignments and self.assignments[l] != item:
                print("WARNING: Custom item assignment %s may be a softlock."
                      % (l, item))
            self.assignments[l] = item

    def try_filter_no_custom_locations(self, items):
        temp = [i for i in items if i not in self.custom_assignments.keys()]
        if temp:
            return temp
        print("WARNING: Forced to use custom item location.")
        return items

    def try_filter_no_custom_items(self, items):
        temp = [i for i in items if i not in self.custom_assignments.values()]
        if temp:
            return temp
        print("WARNING: Forced to use custom item.")
        return items

    def assign_item_location(self, item, location):
        assert location in self.get_valid_locations(item)
        if location in self.custom_assignments:
            assert item == self.custom_assignments[location]
        self._assignable_locations = None
        new_locations = self.get_item_unlocked_locations(item)
        max_rank = max(self.location_ranks)
        self.assignments[location] = item
        if new_locations:
            self.location_ranks[max_rank+1] = new_locations

    def assign_item(self, item, linearity=None):
        self._assignable_locations = None
        assignable_locations = self.get_valid_locations(item)
        if not assignable_locations:
            self.force_custom()
            raise ItemRouterException("No assignable locations: %s." % item)

        candidates = None
        if self.old_goal_requirements:
            candidates = (
                self.requirements_locations[self.old_goal_requirements]
                & assignable_locations)

        if candidates:
            candidates = self.try_filter_no_custom_locations(candidates)
            chosen = random.choice(sorted(candidates))
            self.old_goal_requirements = None
        else:
            if linearity is None:
                linearity = self.linearity
                new_locations = self.get_item_unlocked_locations(item)
                if not new_locations:
                    linearity = linearity ** 2

            ranker = lambda c: (self.get_location_rank(c),
                                self.get_complexity_rank(c), self.rankrand(c))
            candidates = sorted(assignable_locations, key=ranker)
            candidates = self.try_filter_no_custom_locations(candidates)
            if self.goal_requirements is not None:
                sorted_goals = self.get_bottleneck_goals()
                goal = sorted_goals[0]
                if goal != item:
                    temp = [c for c in candidates
                            if c not in self.get_valid_locations(item)]
                    if temp:
                        candidates = temp
            max_index = len(candidates)-1
            weighted_value = (random.random() ** (1-linearity))
            index = int(round(max_index * weighted_value))
            chosen = candidates[index]

        rank = [i for i in self.location_ranks
                if chosen in self.location_ranks[i]]
        assert len(rank) == 1
        self.assign_item_location(item, chosen)

    def check_custom(self):
        locations = self.custom_assignments.keys()
        locations = set(locations) & set(self.assignable_locations)
        for l in locations:
            item = self.custom_assignments[l]
            print("Assigning custom item: %s to %s" % (item, l))
            self.assign_item_location(item, l)
        if locations:
            return True
        return False

    def unassign_item(self, item, ignore=False):
        self._assignable_locations = None
        location = self.get_assigned_location(item)
        if location is None and ignore:
            return
        del(self.assignments[location])
        assert self.get_assigned_location(item) is None

    def clear_assignments(self):
        self.assignments = {}
        self.location_ranks = defaultdict(set)
        self.location_ranks[0] = self.assignable_locations
        self.goal_requirements = None

    def choose_requirements(self):
        if not hasattr(self, "old_goal_requirements"):
            self.old_goal_requirements = None

        candidates = sorted([
            r for r in self.requirements_locations
            if self.requirements_locations[r] & self.unreachable_locations])
        if not candidates:
            self.goal_requirements = None
            return None
        if self.goal_requirements in candidates:
            return self.goal_requirements

        candidates += [c for c in candidates if set(c) & self.assigned_items]
        candidates = sorted(candidates)
        chosen = random.choice(candidates)
        while True:
            candidates = [c for c in candidates if len(c) > len(chosen)
                          and self.requirements_locations[c]
                          < self.requirements_locations[chosen]]
            if candidates:
                newchoice = random.choice(candidates + [chosen])
                if newchoice != chosen:
                    chosen = newchoice
                    continue
            break

        if self.goal_requirements != chosen:
            self.old_goal_requirements = self.goal_requirements
            self.goal_requirements = chosen
        return chosen

    def get_bottleneck_value(self, item):
        return len([location for location in self.unassigned_locations
                    if location not in self.restrictions
                    or item in self.restrictions[location]])

    def get_bottleneck_goals(self):
        sorted_goals = [gr for gr in self.goal_requirements
                        if gr not in self.assigned_items]
        sorted_goals = sorted(
            self.goal_requirements, key=lambda gr: (
                self.get_bottleneck_value(gr), self.rankrand(gr)))
        return sorted_goals

    def try_assign_reqs(self):
        if self.goal_requirements is None:
            return False
        reqs = self.goal_requirements
        reqs = [r for r in reqs if r not in self.assignments.values()]
        if not reqs:
            return True
        if set(reqs) & set(self.custom_assignments.values()):
            return False
        reqs = sorted(
            reqs, key=lambda r: ((self.get_bottleneck_value(r)),
                                 self.rankrand(r)))
        for r in reqs:
            if not self.get_valid_locations(r):
                for r in reqs:
                    self.unassign_item(r, ignore=True)
                return False
            self.assign_item(r)
        return True

    def try_unlock_locations(self, reqs=None):
        if reqs is None:
            reqs = self.unassigned_items
        candidates = [r for r in reqs
                      if self.get_valid_locations(r)
                      and self.get_item_unlocked_locations(r)]
        if not candidates:
            return False

        chosen = None
        if self.goal_requirements:
            if set(candidates) & set(self.goal_requirements):
                candidates = [c for c in candidates
                              if c in self.goal_requirements]
            else:
                sorted_goals = self.get_bottleneck_goals()
                max_index = len(sorted_goals)-1
                index = 0
                goal = sorted_goals[index]
                candidates = self.try_filter_no_custom_items(candidates)
                temp = [c for c in candidates
                        if self.get_item_unlocked_locations(c) &
                        self.get_valid_locations(
                            goal, include_unreachable=True)]
                if temp:
                    max_index = len(candidates)-1
                    index = int(round(max_index * (random.random() ** 2)))
                    chosen = candidates[index]

        if chosen is None:
            candidates = self.try_filter_no_custom_items(candidates)
            chosen = random.choice(candidates)
        self.assign_item(chosen)
        return True

    def prep_requirements(self):
        # this section repeatedly runs the algorithm to ensure stable results
        stdout.write("Analyzing key/lock requirements now.\n")
        stdout.write("Loop 0: ")
        for label in sorted(self.assign_conditions):
            self.get_simplified_requirements(label)
        stdout.write("\n")
        for i in range(1000):
            stdout.write("Loop %s: " % (i+1))
            break_flag = True
            if i % 2:
                conditions = sorted(self.assign_conditions)
            else:
                conditions = sorted(self.assign_conditions, reverse=True)
            #random.shuffle(conditions)  # dunno if this has any effect
            for label in conditions:
                old_requirements = self.get_simplified_requirements(label)
                new_requirements = self.get_simplified_requirements(label,
                                                                    force=True)
                if old_requirements != new_requirements:
                    break_flag = False
            stdout.write("\n")
            if break_flag:
                break
        else:
            raise ItemRouterException("Could not analyze requirements.")

        # this improves RNG stability for some reason?
        for label in sorted(self.assign_conditions):
            if self.get_simplified_requirements(label) == {None}:
                if label in self.assign_conditions:
                    del(self.assign_conditions[label])
                if label in self.definitions:
                    self.definitions.remove(label)

        print("Done analyzing.")

    def assign_everything(self):
        self.prep_requirements()
        print("Assigning items to locations.")
        random.seed(self.routeseed)
        if not hasattr(self, "custom_assignments"):
            self.custom_assignments = {}
        if not hasattr(self, "location_ranks"):
            self.location_ranks = defaultdict(set)
            self.location_ranks[0] = self.assignable_locations
        if not hasattr(self, "goal_requirements"):
            self.goal_requirements = None

        maxloops = len(self.assign_conditions)*5
        for i in range(maxloops):
            if self.check_custom():
                continue
            if not self.unreachable_locations:
                break
            self.choose_requirements()
            success = self.try_unlock_locations(self.goal_requirements)
            if not success:
                success = self.try_assign_reqs()
            if not success:
                success = self.try_unlock_locations()
            if not success:
                if self.custom_assignments:
                    print("Starting over. Attempt %s/%s" % (i+1, maxloops))
                self.clear_assignments()
        else:
            raise ItemRouterException("Could not complete route.")

        self.force_custom()
        #print(self.report)
