from rest_framework import status, viewsets
from rest_framework.response import Response

from core.pagination import BasePagination  # noqa: F401  (re-export)


class BaseModelViewSet(viewsets.ModelViewSet):
    """
    Custom base ViewSet to standardize response structure for all actions.
    """

    def get_queryset(self):
        if not hasattr(self, "queryset") or self.queryset is None:
            raise ValueError(
                f"ViewSet {self.__class__.__name__} is missing a queryset."
            )
        # .all() re-evaluates the queryset per request instead of reusing a
        # cached result across requests.
        return self.queryset.all()

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
        if self.paginator is not None:
            # BasePagination already wraps the payload in the envelope.
            return response
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "List retrieved successfully",
                "data": response.data,
            },
            status=response.status_code,
        )
