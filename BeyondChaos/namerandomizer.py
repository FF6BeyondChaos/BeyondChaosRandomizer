#!/usr/bin/env python3

from utils import (ENEMY_NAMES_TABLE, MODIFIERS_TABLE, MOVES_TABLE,
                   NAMEGEN_TABLE, utilrandom as random)
try:
    modifiers = [line.strip() for line in open(MODIFIERS_TABLE).readlines()]
except FileNotFoundError:
    pass
    # print("Error: " + MODIFIERS_TABLE + " was not found in the custom folder.")
try:
    moves = [line.strip() for line in open(MOVES_TABLE).readlines()]
except FileNotFoundError:
    pass
    # print("Error: " + MOVES_TABLE + " was not found in the custom folder.")
try:
    enemynames = [line.strip() for line in open(ENEMY_NAMES_TABLE).readlines()]
except FileNotFoundError:
    print("Error: " + ENEMY_NAMES_TABLE + " was not found in the tables folder.")

generator = {}
lookback = None
try:
    for line in open(NAMEGEN_TABLE):
        key, values = tuple(line.strip().split())
        generator[key] = values
        if not lookback:
            lookback = len(key)
except FileNotFoundError:
    print("Error: " + NAMEGEN_TABLE + " was not found in the tables folder.")


def generate_name(size=None, maxsize=10):
    if not size:
        size = random.randint(1, 5) + random.randint(1, 5)
        if size < 4:
            size += random.randint(0, 5)

    def has_vowel(text):
        for c in text:
            if c.lower() in "aeiouy":
                return True
        return False

    while True:
        starts = sorted([s for s in generator if s[0].isupper()])
        name = random.choice(starts)
        name = name[:size]
        while len(name) < size:
            key = name[-lookback:]
            if key not in generator and size - len(name) < len(key):
                name = random.choice(starts)
                continue
            if key not in generator or (random.randint(1, 15) == 15
                                        and has_vowel(name[-2:])):
                if len(name) <= size - lookback:
                    if len(name) + len(key) < maxsize:
                        name += " "
                    name += random.choice(starts)
                    continue
                else:
                    name = random.choice(starts)
                    continue

            c = random.choice(generator[key])
            name = name + c

        for ename in enemynames:
            if name == ename:
                name = ""
                break

        if name:
            for ename in enemynames:
                if len(name) > (lookback + 1):
                    length = min(len(name), len(ename))
                    if name[:length] == ename[:length]:
                        name = ""
                        break

        if len(name) >= size:
            enemynames.append(name)
            return name


def generate_attack(web_custom_moves=None):
    global moves, modifiers
    if web_custom_moves:
        moves = web_custom_moves
        modifiers = web_custom_moves

    # One in seven times, make a move with both a prefix and suffix
    if random.randint(1, 7) != 7:
        while True:
            modifier = random.choice(modifiers)
            try:
                move = random.choice(moves)
            except IndexError:
                # The randomizer was unable to find a suffix that, when combined with the prefix,
                #   was less than or equal to 10 in length. Just use the prefix.
                move = ""
                if len(modifier) > 10:
                    # Truncate the modifier if it is too long
                    modifier = modifier[:10]
                break
            if len(modifier) + len(move) <= 10:
                break
    # Six in seven times, make a move with just a suffix
    else:
        modifier = ""
        # Crimdahl: Considering that moves and modifiers are the same list derived from the same table,
        #   I don't see the point in this roll.
        if random.randint(1, 4) != 4:
            candidates = list(moves)
        else:
            candidates = list(modifiers)
        candidates = [c for c in candidates if len(c) >= 3]
        move = random.choice(candidates)

    if len(modifier) + len(move) < 10:
        return ("%s %s" % (modifier, move)).strip()
    # Crimdahl: Do we need to be truncating here if the combined length is over 10?
    return modifier + move


if __name__ == "__main__":
    for i in range(0x100):
        print(generate_name())
