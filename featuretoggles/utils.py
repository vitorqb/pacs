def parse_toggles(str_):
    toggles = {}
    if str_ not in (None, ""):
        for raw in str_.split(","):
            parsed = raw.strip()
            if parsed.startswith("!"):
                toggles[parsed[1:]] = False
            else:
                toggles[parsed] = True
    return toggles


def serialize_toggles(dct):
    elements = []
    for (k, v) in dct.items():
        if v is True:
            elements.append(k)
        else:
            elements.append(f"!{k}")
    return ",".join(elements)
