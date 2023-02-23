from dataclasses import dataclass
from typing import Tuple

from pydantic2ts import generate_typescript_defs

REMOVE_COMMENTS_BEGIN_WITH = ["/*", "*/", "* ", " *"]


@dataclass
class PydanticModel:
    path_pydantic: str
    path_ts: str
    exclude: Tuple[str, ...]


shared_message: Tuple[str, ...] = ("BMessage", "BConfirmation")
exclude = shared_message

models = [
    PydanticModel(
        r".\plants\modules\event\schemas.py",
        r"./ts_api_interfaces/apiTypes_event.ts",
        exclude,
    ),
    PydanticModel(
        r".\plants\modules\image\schemas.py",
        r"./ts_api_interfaces/apiTypes_image.ts",
        exclude,
    ),
    PydanticModel(
        r".\plants\modules\taxon\schemas.py",
        r"./ts_api_interfaces/apiTypes_taxon.ts",
        exclude,
    ),
    PydanticModel(
        r".\plants\modules\plant\schemas.py",
        r"./ts_api_interfaces/apiTypes_plant.ts",
        exclude,
    ),
    PydanticModel(
        r".\plants\shared\message_schemas.py",
        r"./ts_api_interfaces/apiTypes_message.ts",
        (),
    ),
    PydanticModel(
        r".\plants\modules\pollination\schemas.py",
        r"./ts_api_interfaces/apiTypes_pollination.ts",
        (),
    ),
]


def _remove_shared_model(lines: list[str], model_name: str) -> list[str]:
    lines_start = [
        line
        for line in lines
        if line.startswith("export interface " + model_name + " ")
    ]
    if not lines_start:
        return lines
    if len(lines_start) > 1:
        raise ValueError(f"Found more than one line starting with {model_name}")
    line_start = lines_start[0]
    line_start_index = lines.index(line_start)
    line_end_index = None
    for i, line in enumerate(lines[line_start_index + 1 :]):
        if line.startswith("}"):
            line_end_index = line_start_index + i + 1
            break
    if not line_end_index:
        raise ValueError(f"Could not find end of {model_name}")
    lines_new = lines[:line_start_index] + lines[line_end_index + 1 :]
    return lines_new


def remove_shared_models(pydantic_model: PydanticModel):
    with open(pydantic_model.path_ts) as f:
        lines = f.readlines()
    write = False
    for exclude_model in pydantic_model.exclude:
        new_lines = _remove_shared_model(lines, exclude_model)
        if new_lines != lines:
            print(f"Removed {exclude_model} from {pydantic_model.path_ts}")
            lines = new_lines
            write = True
    if write:
        with open(pydantic_model.path_ts, "w") as f:
            f.writelines(lines)


def remove_comments(pydantic_model: PydanticModel):
    with open(pydantic_model.path_ts) as f:
        lines = f.readlines()
    # write = False
    new_lines = [
        line for line in lines if not line.startswith(tuple(REMOVE_COMMENTS_BEGIN_WITH))
    ]
    if len(lines) != len(new_lines):
        with open(pydantic_model.path_ts, "w") as f:
            f.writelines(new_lines)


def _get_models_in_pydantic_file(pydantic_model: PydanticModel) -> set[str]:
    with open(pydantic_model.path_pydantic) as f:
        lines = f.readlines()
    lines_without_spaces = [line.strip() for line in lines]
    lines_with_models = [
        line for line in lines_without_spaces if line.startswith("class")
    ]
    models_with_basemodel = [line.split(" ")[1] for line in lines_with_models]
    models_ = [m[: (m.find("(") or m.find(":"))] for m in models_with_basemodel]
    return set([m for m in models_ if m != "Config"])


def _get_created_definitions_in_ts_file(pydantic_model: PydanticModel) -> set[str]:
    with open(pydantic_model.path_ts) as f:
        lines = f.readlines()
    exports = [line for line in lines if line.strip().startswith("export")]
    if ex := [
        line
        for line in exports
        if not line.startswith("export type")
        and not line.startswith("export interface")
    ]:
        raise ValueError(
            f"Found non type or interface export in {pydantic_model.path_ts}; {ex}"
        )
    exports_without_brackets = [line.replace("{", " ") for line in exports]
    class_names = [line.split(" ")[2] for line in exports_without_brackets]
    return set(class_names)


def get_surplus_models_to_remove(pydantic_model: PydanticModel) -> tuple[str]:
    actual_models = _get_models_in_pydantic_file(model)
    created_definitions = _get_created_definitions_in_ts_file(pydantic_model)
    return tuple(created_definitions - actual_models)


for model in models:
    generate_typescript_defs(model.path_pydantic, model.path_ts)
    models_to_remove = get_surplus_models_to_remove(model)
    model.exclude = models_to_remove
    remove_shared_models(model)
    remove_comments(model)
