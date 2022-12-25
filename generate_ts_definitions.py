from dataclasses import dataclass
from typing import Tuple

from pydantic2ts import generate_typescript_defs

REMOVE_COMMENTS_BEGIN_WITH = ['/*', '*/', '* ', ' *']
HEADER = """import ManagedObject from "sap/ui/base/ManagedObject";

/**
 * @namespace plants.ui.definitions
 */"""


@dataclass
class PydanticModel:
    path_pydantic: str
    path_ts: str
    exclude: Tuple[str, ...]


shared_message: Tuple[str, ...] = ('BMessage', 'BConfirmation')
exclude = shared_message


models = [
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\event_validation.py",
                  r"./ts_api_interfaces/apiTypes_event.ts",
                  exclude),
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\image_validation.py",
                  r"./ts_api_interfaces/apiTypes_image.ts",
                  exclude),
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\taxon_validation.py",
                  r"./ts_api_interfaces/apiTypes_taxon.ts",
                  exclude),
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\property_validation.py",
                  r"./ts_api_interfaces/apiTypes_property.ts",
                  exclude),
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\plant_validation.py",
                  r"./ts_api_interfaces/apiTypes_plant.ts",
                  exclude),
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\selection_validation.py",
                  r"./ts_api_interfaces/apiTypes_selection.ts",
                  exclude),
    PydanticModel(r"C:\workspaces\PycharmProjects\plants_backend\plants\validation\message_validation.py",
                  r"./ts_api_interfaces/apiTypes_message.ts",
                  ()),
]


def _remove_shared_model(lines: list[str], model_name: str) -> list[str]:
    lines_start = [l for l in lines if l.startswith('export interface ' + model_name + ' ')]
    if not lines_start:
        return lines
    if len(lines_start) > 1:
        raise ValueError(f"Found more than one line starting with {model_name}")
    line_start = lines_start[0]
    line_start_index = lines.index(line_start)
    line_end_index = None
    for i, line in enumerate(lines[line_start_index + 1:]):
        if line.startswith('}'):
            line_end_index = line_start_index + i + 1
            break
    if not line_end_index:
        raise ValueError(f"Could not find end of {model_name}")
    lines_new = lines[:line_start_index] + lines[line_end_index + 1:]
    return lines_new


def remove_shared_models(model: PydanticModel):
    with open(model.path_ts) as f:
        lines = f.readlines()
    write = False
    for exclude_model in model.exclude:
        new_lines = _remove_shared_model(lines, exclude_model)
        if new_lines != lines:
            print(f"Removed {exclude_model} from {model.path_ts}")
            lines = new_lines
            write = True
    if write:
        with open(model.path_ts, 'w') as f:
            f.writelines(lines)


def remove_comments(model: PydanticModel):
    with open(model.path_ts) as f:
        lines = f.readlines()
    # write = False
    new_lines = [l for l in lines if not l.startswith(tuple(REMOVE_COMMENTS_BEGIN_WITH))]
    if len(lines) != len(new_lines):
        with open(model.path_ts, 'w') as f:
            f.writelines(new_lines)


# def insert_header(model: PydanticModel):
#     with open(model.path_ts) as f:
#         lines = f.readlines()
#     lines.insert(0, HEADER)
#     with open(model.path_ts, 'w') as f:
#         f.writelines(lines)


def _get_models_in_pydantic_file(model: PydanticModel) -> set[str]:
    with open(model.path_pydantic) as f:
        lines = f.readlines()
    lines_without_spaces = [l.strip() for l in lines]
    lines_with_models = [l for l in lines_without_spaces if l.startswith('class')]
    models_with_basemodel = [l.split(' ')[1] for l in lines_with_models]
    models = [m[:(m.find('(') or m.find(':'))] for m in models_with_basemodel]
    return set([m for m in models if m != 'Config'])


def _get_created_definitions_in_ts_file(model: PydanticModel) -> set[str]:
    with open(model.path_ts) as f:
        lines = f.readlines()
    exports = [l for l in lines if l.strip().startswith('export')]
    if ex := [l for l in exports if not l.startswith('export type') and not l.startswith('export interface')]:
        raise ValueError(f"Found non type or interface export in {model.path_ts}; {ex}")
    exports_without_brackets = [l.replace('{', ' ') for l in exports]
    class_names = [l.split(' ')[2] for l in exports_without_brackets]
    return set(class_names)


def get_surplus_models_to_remove(model: PydanticModel) -> tuple[str]:
    actual_models = _get_models_in_pydantic_file(model)
    created_definitions = _get_created_definitions_in_ts_file(model)
    return tuple(created_definitions - actual_models)


for model in models:
    models_to_remove = get_surplus_models_to_remove(model)
    generate_typescript_defs(model.path_pydantic, model.path_ts)  # doesn't work anyway:, exclude=models_to_remove)
    model.exclude = models_to_remove
    remove_shared_models(model)
    remove_comments(model)
    # insert_header(model)
