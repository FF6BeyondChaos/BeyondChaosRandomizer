def test_esper_allocation():
    from esperrandomizer import get_espers
    from character import get_characters
    from random import Random
    from io import BytesIO

    random = Random()
    char_ids = list(range(12)) + [13]
    source_file = "D:\\Beyond Chaos\\ff3.smc"
    espers = get_espers(BytesIO(open(source_file, "rb").read()))
    characters = [c for c in get_characters() if c.id in char_ids]
    preassigned_espers = random.sample(espers, len(characters))
    preassignments = {e: c for (e, c) in zip(preassigned_espers, characters)}

    test_range = 1000
    crusader_id = 15
    ragnarok_id = 16

    average_users_per_tier = {}
    average_users_per_esper = {}
    esperless_users = 0
    unique_users = set()
    for index in range(test_range):
        espers_per_tier = {}
        users_per_tier = {}
        users_per_esper = {}
        for e in espers:
            num_users = 1
            if e.id not in [crusader_id, ragnarok_id] and 20 - (4 * e.rank) >= random.random() * 100:
                num_users += 1
                while num_users < len(char_ids) and random.choice([True] + [False] * (e.rank + 2)):
                    num_users += 1
            users = random.sample(characters, num_users)
            if e in preassignments:
                c = preassignments[e]
                if c not in users:
                    users[0] = c
                    assert c in users
            for user in users:
                unique_users.add(user)
            # chars_requiring_espers = [c for c in chars_requiring_espers if c not in [u.id for u in users]]
            espers_per_tier[e.rank] = espers_per_tier.get(e.rank, 0) + 1
            users_per_tier[e.rank] = users_per_tier.get(e.rank, 0) + num_users
            users_per_esper[e.name] = users_per_esper.get(e.name, 0) + num_users
        assert len(unique_users) == len(char_ids)


        for key, value in users_per_tier.items():
            # Average the number of users per tier by dividing by the number of users by the number of espers in that tier
            users_per_tier[key] = value / espers_per_tier[key]
            average_users_per_tier[key] = average_users_per_tier.get(key, 0) + users_per_tier.get(key, 0)

        # Average the number of users per tier by dividing by the number of users by the number of espers in that tier
        for key, value in users_per_esper.items():
            average_users_per_esper[key] = average_users_per_esper.get(key, 0) + users_per_esper.get(key, 0)

    for key, value in average_users_per_tier.items():
        average_users_per_tier[key] = average_users_per_tier.get(key, 0) / test_range

    for key, value in average_users_per_esper.items():
        average_users_per_esper[key] = average_users_per_esper.get(key, 0) / test_range

    print("Average esperless characters: " + str(esperless_users / test_range))
    print("Average users by esper tier (Original): " + str(average_users_per_tier))
    print("Average users by esper (Original): " + str(average_users_per_esper))

    print("\n")
    average_users_per_tier = {}
    average_users_per_esper = {}
    from math import pow

    for index in range(test_range):
        espers_per_tier = {}
        users_per_tier = {}
        users_per_esper = {}
        for e in espers:
            num_users = 1
            if e.id not in [crusader_id, ragnarok_id]:
                while num_users < len(char_ids) and 90 - (18 * e.rank + pow(1.25, num_users)) >= random.random() * 100:
                    num_users += 1
            espers_per_tier[e.rank] = espers_per_tier.get(e.rank, 0) + 1
            users_per_tier[e.rank] = users_per_tier.get(e.rank, 0) + num_users
            users_per_esper[e.name] = users_per_esper.get(e.name, 0) + num_users
        for key, value in users_per_tier.items():
            users_per_tier[key] = value / espers_per_tier[key]
            average_users_per_tier[key] = average_users_per_tier.get(key, 0) + users_per_tier.get(key, 0)
        for key, value in users_per_esper.items():
            average_users_per_esper[key] = average_users_per_esper.get(key, 0) + users_per_esper.get(key, 0)

    for key, value in average_users_per_tier.items():
        average_users_per_tier[key] = average_users_per_tier.get(key, 0) / test_range

    for key, value in average_users_per_esper.items():
        average_users_per_esper[key] = average_users_per_esper.get(key, 0) / test_range

    print("Average users by esper tier (Modified): " + str(average_users_per_tier))
    print("Average users by esper (Modified): " + str(average_users_per_esper))


if __name__ == "__main__":
    test_esper_allocation()