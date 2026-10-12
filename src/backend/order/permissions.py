
from rest_framework.permissions import BasePermission


class IsOrderOwner(BasePermission):
    """
    Allows access only to the customer who owns the order.
    """

    def has_object_permission(self, request, view, obj):
        return obj.customer.user == request.user


class IsOrderItemOwner(BasePermission):
    """
    Allows access only to the customer who owns the order item.
    """

    def has_object_permission(self, request, view, obj):
        return obj.order.customer.user == request.user


class IsBillOwner(BasePermission):
    """
    Allows access only to the customer who owns the bill.
    """

    def has_object_permission(self, request, view, obj):
        return obj.cart.customer.user == request.user

