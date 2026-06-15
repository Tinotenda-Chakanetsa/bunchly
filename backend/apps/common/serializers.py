"""Shared serializer base classes."""
from __future__ import annotations

from rest_framework import serializers
from rest_framework.relations import ManyRelatedField, RelatedField


class TenantScopedModelSerializer(serializers.ModelSerializer):
    """ModelSerializer that confines relational choices to the request tenant.

    Any related field whose target model has a ``tenant`` column has its
    queryset filtered to the current tenant. This prevents a client from
    assigning another tenant's object as a foreign key (an IDOR vector).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        tenant = getattr(request, "tenant", None) if request else None
        if tenant is None:
            return
        for field in self.fields.values():
            related = (
                field.child_relation
                if isinstance(field, ManyRelatedField)
                else field
            )
            queryset = getattr(related, "queryset", None)
            if isinstance(related, RelatedField) and queryset is not None:
                model = queryset.model
                if any(f.name == "tenant" for f in model._meta.fields):
                    related.queryset = queryset.filter(tenant=tenant)
