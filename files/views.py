import boto3
import os

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .utils import encrypt_file, generate_key, decrypt_file
from .models import File


class UploadAndEncryptFileView(View):
    def get(self, request):
        return render(request, 'upload_file.html')

    def post(self, request):
        if request.FILES.get('file'):
            uploaded_file = request.FILES['file']
            file_content = uploaded_file.read()

            try:
                key = generate_key()
                encrypted_data = encrypt_file(file_content, key)

                if settings.USE_S3:
                    s3 = boto3.client(
                        's3',
                        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                    )
                    s3_key = f'encrypted/{uploaded_file.name}'
                    s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key, Body=encrypted_data)
                    file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                else:
                    local_file_path = os.path.join(settings.LOCAL_STORAGE_PATH, uploaded_file.name)
                    with open(local_file_path, 'wb') as f:
                        f.write(encrypted_data)
                    file_url = local_file_path

                # Save the encryption key to the database
                File.objects.create(
                    file_name=uploaded_file.name,
                    encryption_key=key.decode('utf-8')
                )

                return render(request, 'upload_success.html', {
                    'file_url': file_url,
                    'encryption_key': key.decode('utf-8')
                })
            except Exception as e:
                return render(request, 'upload_file.html', {'error': str(e)})

        return render(request, 'upload_file.html', {'error': 'File not uploaded'})



class ListUploadedFilesView(View):

    def get(self, request):
        files = File.objects.all()  # TODO: Fetch via external KMS
        return render(request, 'list_files.html', {'files': files})



class DecryptFileView(View):

    def get(self, request, file_name):

        try:
            record = File.objects.get(file_name=file_name)
            key = record.encryption_key.encode('utf-8')
        except File.DoesNotExist:
            return JsonResponse({'error': 'File not found'}, status=404)

        if settings.USE_S3:
            s3 = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            s3_key = f'encrypted/{file_name}'
            response = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=s3_key)
            encrypted_data = response['Body'].read()
        else:
            file_path = os.path.join(settings.LOCAL_STORAGE_PATH, file_name)
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()

        decrypted_data = decrypt_file(encrypted_data, key)

        response = HttpResponse(decrypted_data, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename={file_name}'
        return response