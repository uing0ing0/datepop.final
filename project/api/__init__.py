from ninja import NinjaAPI

from .image import router as image_router

api = NinjaAPI()
api.add_router("/image", image_router)
