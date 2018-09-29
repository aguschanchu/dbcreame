import io
import os
from typing import List
from google.cloud import vision
from google.cloud.vision import types
from django.conf import settings
from db.models import ImagenVisionAPI


class ImageDetector:
    def __init__(self):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS

        self.client = vision.ImageAnnotatorClient()

    def request_image_labels(self, imagen: ImagenVisionAPI) -> List['ImageLabel']:
        with io.open(settings.BASE_DIR+imagen.image.url, 'rb') as image_file:
            content = image_file.read()
        image = types.Image(content=content)

        # Performs label detection on the image file
        response = self.client.label_detection(image=image)
        return ImageLabel.from_entity_annotation_list(response.label_annotations)


class ImageLabel:
    def __init__(self, mid: str, description: str, score: float, topicality: float):
        self.mid: str = mid
        self.description: str = description
        self.score: float = score
        self.topicality: float = topicality

    @staticmethod
    def from_entity_annotation(annotation) -> 'ImageLabel':
        return ImageLabel(annotation.mid,
                          annotation.description,
                          annotation.score,
                          annotation.topicality)

    @staticmethod
    def from_entity_annotation_list(annotation_list) -> List['ImageLabel']:
        label_list = []
        for annotation in annotation_list:
            label_list.append(
                ImageLabel(annotation.mid,
                           annotation.description,
                           annotation.score,
                           annotation.topicality)
            )

        return label_list
