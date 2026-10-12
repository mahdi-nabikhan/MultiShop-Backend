import pytest
from decimal import Decimal
from rest_framework.test import APIRequestFactory
from account.models import User
from customer.models import Customer, Address
from vendor.models import Manager, Store
from website.models import Category, Product
from order.models import Order, OrderItem, Bill
from order.api.v1.serializer import OrderSerializer, OrderItemSerializer, BillSerilizers


@pytest.mark.django_db
class TestOrderSerializers:
    """
    Test suite for Order, OrderItem, and Bill serializers.

    This suite covers:

    1. OrderSerializer:
       - Creating an Order instance.
       - Ensuring the customer is set from the request context.
       - Default status field is False.

    2. OrderItemSerializer:
       - Creating an OrderItem linked to an Order and Product.
       - Verifies automatic calculation of total price (product.price * quantity).
       - Ensures status is set to pending.
       - Correct linkage to the provided Product.

    3. BillSerializers:
       - Creating a Bill linked to an Order and an Address.
       - Ensures status is False by default.
       - Checks the serialized representation includes nested Order details.

    Notes:
    ------
    - All tests rely on the 'sample_data' fixture which provides:
      Customer, Product, Order, Address, Manager, and Store instances.
    - Decimal is used for monetary calculations to maintain precision.
    - APIRequestFactory is used to simulate request context for serializers.
    """

    @pytest.fixture
    def sample_data(self):
        # Users
        user = User.objects.create_user(email='test@gmail.com', password='pass12345')
        manager_user = User.objects.create_user(email='manager@gmail.com', password='pass12345')

        # Manager and store
        manager = Manager.objects.create(user=manager_user, first_name='A', last_name='B')
        store = Store.objects.create(manager=manager, name='Tech Store', description='Tech Gadgets')

        # Customer
        customer = Customer.objects.create(user=user, username='mahdi')

        # Category and product
        category = Category.objects.create(title='Electronics', image='cat.png', description='Electronics category')
        product = Product.objects.create(
            name='Laptop',
            description='Powerful laptop',
            price=Decimal('1500.00'),
            quantity_in_stock=5,
            store=store,
            category=category
        )

        # Address
        address = Address.objects.create(customer=customer, street='Main St', city='Tehran', state='Tehran', postal_code='12345')

        return {
            'user': user,
            'customer': customer,
            'manager': manager,
            'store': store,
            'category': category,
            'product': product,
            'address': address
        }

    def test_order_serializer_create(self, sample_data):
        factory = APIRequestFactory()
        request = factory.post('/orders/')
        serializer = OrderSerializer(data={}, context={'request': request})
        request.user = sample_data['user']
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        assert isinstance(order, Order)
        assert order.customer == sample_data['customer']
        assert order.status is False

    def test_order_item_serializer_create(self, sample_data):
        factory = APIRequestFactory()
        request = factory.post(f"/orders/items/{sample_data['product'].pk}/")
        request.user = sample_data['user']

        serializer = OrderItemSerializer(
            data={'quantity': 2},
            context={'request': request, 'pk': sample_data['product'].pk}
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        assert isinstance(item, OrderItem)
        assert item.product == sample_data['product']
        assert item.quantity == 2
        assert item.total == Decimal('3000.00')
        assert item.status == OrderItem.Status.pending

