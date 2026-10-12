from rest_framework import serializers
from order.models import *
from customer.models import *
from website.models import *
from vendor.api.v1.serializers import ProductSerializer
from ...services import CartService
from django.db import transaction


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for the Order model, used for creating and representing customer orders.

    Responsibilities
    ----------------
    - Serialize Order instances to JSON for API responses.
    - Validate and create new Order instances for the authenticated customer.
    - Ensures that the `customer` field is automatically set to the requesting user.

    Attributes
    ----------
    Meta.model : Order
        - The model associated with this serializer.
    Meta.fields : '__all__'
        - All fields of the Order model are included.
    Meta.read_only_fields : ('customer',)
        - The `customer` field is read-only and set automatically from the request.

    Methods
    -------
    create(self, validated_data)
        - Automatically sets `customer` to the currently authenticated user.
        - Creates and returns a new Order instance.

    Usage
    -----
        # Create a new order for the authenticated user
        POST /api/v1/orders/
        {
            "field1": "value1",
            "field2": "value2"
        }
        -> returns the created order with all fields, including customer

    Notes
    -----
    - The serializer assumes that `request` is passed in the context.
    - Only authenticated users can create orders; otherwise, an error will occur.
    - Typically used in conjunction with `OrderListApiView` or other Order-related API views.
    """
    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('customer',)

    def create(self, validated_data):
        validated_data['customer'] = Customer.objects.get(user=self.context['request'].user)
        return Order.objects.create(**validated_data)


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem model, handling creation and representation of order items.

    Responsibilities
    ----------------
    - Serialize OrderItem instances to JSON for API responses.
    - Validate and create new OrderItem instances linked to the authenticated customer's active order.
    - Automatically associates the item with the correct Order and Product.

    Attributes
    ----------
    Meta.model : OrderItem
        - The model associated with this serializer.
    Meta.fields : '__all__'
        - Includes all fields of the OrderItem model.
    Meta.read_only_fields : ['order', 'product']
        - 'order' and 'product' are set automatically and cannot be provided directly.

    Methods
    -------
    create(self, validated_data)
        - Retrieves the authenticated customer from request context.
        - Gets or creates the active Order (status=False) for the customer.
        - Associates the OrderItem with the provided product (`pk` from context).
        - Returns the created OrderItem instance.

    to_representation(self, instance)
        - Customizes serialized output to include detailed Product information using ProductSerializer.

    Usage
    -----
        # Create a new OrderItem for product ID 10
        POST /api/v1/order-item/create/10/
        {
            "quantity": 2
        }
        -> returns serialized OrderItem with nested product details

    Notes
    -----
    - Requires `request` and `pk` (product ID) to be passed in serializer context.
    - The `order` field is automatically linked to the customer's active order.
    - Ideal for building shopping cart and checkout functionality.
    - Supports nested serialization for better frontend consumption.
    """
    class Meta:
        model = OrderItem
        fields = '__all__'
        read_only_fields = ['order', 'product']

    def create(self, validated_data):
        request = self.context.get('request')
        customer = Customer.objects.get(user=request.user)
        order,created = Order.objects.get_or_create(customer=customer, status=False)
        product = Product.objects.get(pk=self.context.get('pk'))

        validated_data['order'] = order
        validated_data['product'] = product
        return OrderItem.objects.create(**validated_data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['product'] = ProductSerializer(instance.product).data
        return rep
    
    
    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Quantity must be greater than zero."
            )

        if self.instance is not None:
            product = self.instance.product
        else:
            product_id = self.context.get("pk")
            product = Product.objects.filter(
                pk=product_id
            ).first()

        if not product:
            raise serializers.ValidationError(
                "Product does not exist."
            )

        if value > product.quantity_in_stock:
            raise serializers.ValidationError(
                "Requested quantity exceeds available stock."
            )

        return value





class BillSerilizers(serializers.ModelSerializer):

    class Meta:
        model = Bill
        fields = "__all__"
        read_only_fields = [
            "cart",
            "address",
        ]

    def validate(self, attrs):

        request = self.context.get("request")
        address_pk = self.context.get("pk")

        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Authentication is required."
            )

        if not address_pk:
            raise serializers.ValidationError(
                {"address": "Address is required."}
            )

        customer = Customer.objects.filter(
            user=request.user
        ).first()

        if not customer:
            raise serializers.ValidationError(
                {"customer": "Customer does not exist."}
            )

        address = Address.objects.filter(
            pk=address_pk,
            customer=customer
        ).first()

        if not address:
            raise serializers.ValidationError(
                {
                    "address":
                    "Address does not exist or does not belong to you."
                }
            )

        cart = CartService.get_cart(
            customer_id=customer.id
        )

        if not cart:
            raise serializers.ValidationError(
                {
                    "order":
                    "Cannot create a bill for an empty cart."
                }
            )

        self.customer = customer
        self.address = address
        self.cart = cart

        return attrs

    def create(self, validated_data):

        with transaction.atomic():

            order = Order.objects.create(
                customer=self.customer,
                status=False,
            )

            for product_id, quantity in self.cart.items():

                product = Product.objects.filter(
                    pk=product_id
                ).first()

                if not product:
                    raise serializers.ValidationError(
                        {
                            "product":
                            f"Product {product_id} does not exist."
                        }
                    )

                if quantity > product.quantity_in_stock:
                    raise serializers.ValidationError(
                        {
                            "product":
                            f"Requested quantity for "
                            f"'{product}' exceeds available stock."
                        }
                    )

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                )

            validated_data["cart"] = order
            validated_data["address"] = self.address

            bill = Bill.objects.create(
                **validated_data
            )

        return bill

    def to_representation(self, instance):

        response = super().to_representation(instance)

        response["cart"] = OrderSerializer(
            instance.cart
        ).data

        return response






class CartItemSerializer(serializers.Serializer):
    product = ProductSerializer()
    quantity = serializers.IntegerField()
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )


class CartSerializer(serializers.Serializer):
    items = CartItemSerializer(many=True)
    total_quantity = serializers.IntegerField()
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2
    )

class CartAddSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1,
        default=1,
        required=False,
    )
    
    
class CartMessageSerializer(serializers.Serializer):
    detail = serializers.CharField()
    
    
    



class AddToCartSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(
        min_value=1
    )

    def validate_quantity(self, value):
        product_id = self.context.get("product_id")

        product = Product.objects.filter(
            pk=product_id
        ).first()

        if not product:
            raise serializers.ValidationError(
                "Product does not exist."
            )

        if value > product.quantity_in_stock:
            raise serializers.ValidationError(
                "Requested quantity exceeds available stock."
            )

        return value


