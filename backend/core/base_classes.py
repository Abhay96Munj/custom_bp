from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework import pagination
from django.conf import settings
# from boto3 import client
import logging
import datetime
# from botocore.signers import CloudFrontSigner
# import rsa

logger = logging.getLogger("Project_Name")

# def get_presigned_url(file_key, expiration=600, bucket_name_check=None):
#     """
#     Generate a pre-signed URL for a private S3 file.
#     :param file_key: The key of the file in the S3 bucket.
#     :param expiration: URL expiry time in seconds (default: 1 hour).
#     :return: Pre-signed URL as a string.
#     """
#     logger.info("Calling AWS S3 generate_presigned_url API")

#     try:
#         s3_client = client(
#             "s3",
#             aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#             region_name=settings.AWS_S3_REGION_NAME,
#         )
#         bucket_name = settings.AWS_INSTALLER_BUCKET_NAME if bucket_name_check else settings.AWS_STORAGE_BUCKET_NAME

#         url = s3_client.generate_presigned_url(
#             "get_object",
#             Params={
#                 "Bucket": bucket_name,
#                 "Key": file_key,
#             },
#             ExpiresIn=expiration,
#         )

#         return url
    
#     except Exception as e:
#         logger.error(f"AWS S3 presigned URL generation failed: {str(e)}")
#         return None


class BasePagination(pagination.PageNumberPagination):
    def get_paginated_response(self, data):
        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Data fetched successfully.",
                "data": {
                    "count": self.page.paginator.count,
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                    "data": data,
                },
            }
        )


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Custom base ViewSet to standardize response structure for all actions.
    """

    def get_queryset(self):
        """Ensure queryset is always available"""
        if not hasattr(self, "queryset") or self.queryset is None:
            raise ValueError(
                f"ViewSet {self.__class__.__name__} is missing a queryset."
            )
        return self.queryset

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "Created successfully",
                "data": response.data,
            },
            status=response.status_code,
        )

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "Updated successfully",
                "data": response.data,
            },
            status=response.status_code,
        )

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Deleted successfully",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "Retrieved successfully",
                "data": response.data,
            },
            status=response.status_code,
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "List retrieved successfully",
                "data": response.data,
            },
            status=response.status_code,
        )
