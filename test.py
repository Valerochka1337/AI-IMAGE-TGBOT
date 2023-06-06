import re

def parse_response(text):
    pattern = r"\[IMAGE\]\{(.+)\}"
    matches = re.findall(pattern, text)
    image_descriptions = iter(matches)
    print([i for i in image_descriptions])
    result = {"data": []}
    parts = re.split(pattern, text)
    print([i for i in parts])

    for part in parts:
        if part in matches:
            if len(part) > 1:
                result["data"].append({"type": "image", "content": part})
        elif part:
            if len(part) > 1:
                result["data"].append({"type": "text", "content": part})

    return result

print(parse_response("""Конечно! Гориллы - это крупные приматы, которые обитают в тропических лесах и горах Африки. Они являются одними из ближайших родственников человека и обладают сходными чертами, такими как большой размер мозга и социальная организация.

Гориллы делятся на два вида: восточные гориллы и западные гориллы. Восточные гориллы обитают в Восточной Африке, а западные гориллы - в Западной Африке. Они оба находятся под угрозой их вымирания из-за потери мест обитания и браконьерства.

Вот две фотографии горилл для вас:

[IMAGE]{A photo of a male silverback gorilla sitting on a rock and looking off into the distance}
[IMAGE]{A photo of a mother gorilla with her baby clinging to her back as they walk through the forest}"""))