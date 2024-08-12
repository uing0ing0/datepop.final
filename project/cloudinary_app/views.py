# from django.shortcuts import render, redirect
# from django.http import HttpResponse
# from django.core.files.storage import FileSystemStorage
# from .models import ImageModel
# from django.template import TemplateDoesNotExist
# import logging

# # 로거 설정
# logger = logging.getLogger(__name__)

# def image_upload_view(request):
#     if request.method == 'POST':
#         uploaded_image = request.FILES.get('uploaded_image')
#         if uploaded_image:
#             fs = FileSystemStorage()
#             name = fs.save(uploaded_image.name, uploaded_image)
#             model_instance = ImageModel(uploaded_image=fs.url(name))
#             model_instance.save()
#             return redirect('success')
#         else:
#             return HttpResponse("No image uploaded.")
#     try:
#         print('dddddd')
#         response = render(request, 'cloudinary_app/index.html')
#         print("Response content:", response.content)  # Check what's being rendered
#         return response
#     except TemplateDoesNotExist:
#         logger.error('The template does not exist.')
#         return HttpResponse("The requested template does not exist.", status=404)

# def success_view(request):
#     return HttpResponse("Image uploaded successfully!")




# from django.shortcuts import render, HttpResponse
# from django.template import TemplateDoesNotExist
# import logging
# import os
# from django.conf import settings

# # Setting up logging
# logger = logging.getLogger(__name__)

# def image_upload_view(request):
#     try:
#         # This will help confirm that the correct template path is being used
#         template_path = os.path.join(settings.BASE_DIR, 'cloudinary_app', 'templates', 'cloudinary_app', 'index.html')
#         logger.debug(f"Checking template path: {template_path}")

#         # Attempt to render the index.html template
#         response = render(request, 'cloudinary_app/index.html')
#         logger.debug(f"Rendered content size: {len(response.content)} bytes")

#         return response
#     except TemplateDoesNotExist:
#         logger.error(f"The template does not exist at {template_path}")
#         return HttpResponse("The requested template does not exist.", status=404)








# from django.shortcuts import render, HttpResponse, redirect
# from django.core.files.storage import FileSystemStorage
# from .models import ImageModel
# import logging

# logger = logging.getLogger(__name__)

# def image_upload_view(request):
#     if request.method == 'POST':
#         uploaded_image = request.FILES.get('uploaded_image')
#         if uploaded_image:
#             fs = FileSystemStorage()
#             name = fs.save(uploaded_image.name, uploaded_image)
#             url = fs.url(name)
#             model_instance = ImageModel(uploaded_image=url)
#             model_instance.save()
#             return HttpResponse("Image uploaded successfully!")  # Redirect to a success page or you can handle it here
#         else:
#             return HttpResponse("Please upload a valid image.")

#     return render(request, 'cloudinary_app/index.html')




from django.shortcuts import render, HttpResponse, redirect
from django.core.files.storage import FileSystemStorage
from .models import ImageModel
import cloudinary.uploader

def image_upload_view(request):
    if request.method == 'POST':
        uploaded_image = request.FILES.get('uploaded_image')
        if uploaded_image:
            fs = FileSystemStorage()
            filename = fs.save(uploaded_image.name, uploaded_image)
            uploaded_image_url = fs.url(filename)

            # Upload to Cloudinary
            response = cloudinary.uploader.upload(fs.path(filename), 
                folder = "demo_uploads",
                transformation = [
                    {'effect': 'saturation:50'},
                    {'effect': 'contrast:30'},
                    {'effect': 'brightness:17'},
                    {'effect': 'auto_color'},
                    {'effect': 'vibrance:50'},
                    {'effect': 'red:5'},
                ]
            )
            print(response)

            # Save to ImageModel
            model_instance = ImageModel(
                uploaded_image=uploaded_image_url,
                processed_image=response['secure_url']  # Using secure_url for HTTPS
            )
            model_instance.save()

            return HttpResponse('success')
        else:
            return HttpResponse("Please upload a valid image.")

    return render(request, 'cloudinary_app/index.html')

def success_view(request):
    return HttpResponse("Image uploaded and processed successfully!")
