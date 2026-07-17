"""
Standalone pagination module.

DEFAULT_PAGINATION_CLASS points here. This module must not import
rest_framework.generics/viewsets — DRF resolves the pagination class while
those modules are still initializing, so importing them back would create a
circular import.
"""

from rest_framework import pagination, status
from rest_framework.response import Response


class BasePagination(pagination.PageNumberPagination):
    """Paginated responses wrapped in the project's standard envelope."""

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
