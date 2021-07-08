from gameobjects.character import Character


def read_characters(file_name):
    character_list = []
    for i, line in enumerate(open(file_name)):
        line = line.strip()
        if line.startswith('#'):
            continue

        line = " ".join(line.split())
        c = Character(*line.split(','))
        c.id = i
        character_list.append(c)
    return character_list
