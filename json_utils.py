import json
import os
import config


def load(file_path):
    #print(f"-- load: {file_path}")

    if not os.path.exists(file_path):
        print(f"** missing file {file_path}")
        return None
    else:
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"** cannot load {file_path}")
            print(e)

def dump(data, file_path) -> None:
    print(f"-- save: {file_path}")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def dump_meta(data, aids) -> None:
    joined_aids = '_'.join([str(aid) for aid in aids])
    file_path = f"{config.PAGES_DIR}/{joined_aids}/_meta_.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_meta_for_aids(aids):
    joined_aids = '_'.join([str(aid) for aid in aids])
    return load(f"{config.PAGES_DIR}/{joined_aids}/_meta_.json")
