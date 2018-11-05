from typing import Tuple
from .text_filer import name_in_name
from.geometry_filter import geometry_filter
from db.models import Objeto


def thing_files_filter(thing: Objeto, plot_graph: bool = False, timeout=60):
    if len(thing.files.all()) <= 1:
        return True

    # Filter things by their names
    name_in_name(thing)

    # Filter things by geometry
    geometry_filter(thing)

    return True
