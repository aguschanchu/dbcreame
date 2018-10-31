from django.utils import timezone
from db.models import Objeto

def license_filter(thing: Objeto) -> bool:
    attr = thing.external_id.thingiverse_attributes
    # License filter
    if attr.license == None:
        return True
    if "non-commercial" in attr.license.lower():
        return False

    return True


def image_filter(thing: Objeto) -> bool:
    if thing.main_image is None:
        return False
    # Image size filter
    height = thing.main_image.width
    width = thing.main_image.height
    if abs(width / height - 4 / 3) > 1/3:
        return False

    return True


def category_filter(thing: Objeto) -> bool:
    # Filter by category
    category_list = ['3d printing', 'printer', '3d printer accessories']
    unwanted_categories = list(filter(
        lambda cat: any(category in cat.lower() for category in category_list),
        [c.name for c in thing.category.all()])
    )
    if len(unwanted_categories) is not 0:
        return False  # Filter by the categories

    return True


def likes_filter(thing: Objeto) -> bool:
    attr = thing.external_id.thingiverse_attributes
    # Filter by date & likes
    today = timezone.now()
    delta_time = today - attr.added
    if delta_time.days >= 30:
        if attr.like_count <= 500 or attr.download_count <= 500:
            return False
    elif 10 <= delta_time.days < 30:
        if attr.like_count <= 100 or attr.download_count <= 100:
            return False
    elif delta_time.days < 10:
        if attr.like_count <= 10 or attr.download_count <= 20:
            return False

    return True


def nsfw_filter(thing: Objeto) -> bool:
    # NSFW filter
    nsfw_word_list = ['nsfw', 'sexy', 'nude']
    if any(nsfw_word in thing.name.lower() for nsfw_word in nsfw_word_list):
        return False  # Filter by the title
    if any(nsfw_word in thing.description.lower() for nsfw_word in nsfw_word_list):
        return False  # Filter by the description
    tags = list(filter(
        lambda tag: any(nsfw_word in tag.name.lower() for nsfw_word in nsfw_word_list),
        [t for t in thing.tags.all()])
    )
    if len(tags) is not 0:
        return False  # Filter by the tags

    return True


def keyword_filter(thing: Objeto) -> bool:
    # Filter by keyword
    unwanted_words = ['parametric', 'customizable', 'robot', 'chain', 'acrylic', 'backlash',
                      'laser', 'gear', 'lego', 'engine', 'drone', 'openrc', 'shower', 'generator']
    if any(word in thing.name.lower() for word in unwanted_words):
        return False  # Filter by the title
    if any(word in thing.description.lower() for word in unwanted_words):
        return False  # Filter by the description
    unwanted_tags = list(filter(
        lambda tag: any(word in tag.name.lower() for word in unwanted_words),
        [t.name for t in thing.tags.all()])
    )
    if len(unwanted_tags) is not 0:
        return False  # Filter by the tags

    return True


def thing_files_filter(thing: Objeto) -> bool:
    '''
    El filtro de extensiones se dejo para la instancia de importacion de archivos, de modo que todos estos, sean
    aplicados al finalizar la importacion parcial.
    TODO: Como consecuencia de lo anterior, podria una Thing quedar sin archivos.
    '''
    attr = thing.external_id.thingiverse_attributes
    # Filter by number of files
    if attr.original_file_count > 15:
        return False

    return True


def complete_filter_func(thing: Objeto) -> bool:
    if not license_filter(thing):
        return False
    if not image_filter(thing):
        return False
    if not category_filter(thing):
        return False
    if not likes_filter(thing):
        return False
    if not nsfw_filter(thing):
        return False
    if not keyword_filter(thing):
        return False
    if not thing_files_filter(thing):
        return False

    return True