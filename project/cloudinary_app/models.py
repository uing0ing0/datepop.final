from django.db import models

class ImageModel(models.Model):
    uploaded_image = models.ImageField(upload_to='uploads/')
    processed_image = models.ImageField(upload_to='processed/', blank=True, null=True)

    def __str__(self):
        return f"Image {self.pk}"
