
from decimal import Decimal
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.urls import reverse
from order.models import Order, OrderItem, Bill
from order.services import CartService
from vendor.models import Manager, Store
from website.models import Product, Category
from customer.models import Customer, Address


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def setup_data(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = User.objects.create_user(
        email="test@gmail.com",
        password="testpassword123",
    )

    manager_user = User.objects.create_user(
        email="manager@gmail.com",
        password="managerpassword123",
    )

    customer = Customer.objects.create(
        user=user,
        username="mahdi",
    )

    manager = Manager.objects.create(
        user=manager_user,
    )

    category = Category.objects.create(
        title="Electronics",
        image="cat.png",
        description="Electronics category",
    )

    store = Store.objects.create(
        manager=manager,
        name="Test Store",
    )

    product = Product.objects.create(
        name="Laptop",
        description="Powerful laptop",
        price=Decimal("1500.00"),
        quantity_in_stock=5,
        store=store,
        category=category,
    )

    address = Address.objects.create(
        customer=customer,
        street="Main St",
        city="Tehran",
        state="Tehran",
        postal_code="12345",
    )

    return {
        "user": user,
        "manager_user": manager_user,
        "customer": customer,
        "manager": manager,
        "store": store,
        "category": category,
        "product": product,
        "address": address,
    }


@pytest.mark.django_db
class TestOrderViews:

    def test_order_list_create(self, api_client, setup_data):
        user = setup_data["user"]
        customer = setup_data["customer"]

        api_client.force_authenticate(user=user)

        url = "/order/api/v1/orders/"
        response = api_client.post(
            url,
            {"customer": customer.id},
            format="json",
        )

        assert response.status_code == 201, response.data
        assert Order.objects.filter(customer=customer).exists()

    def test_order_item_create_list(self, api_client, setup_data):
        user = setup_data["user"]
        customer = setup_data["customer"]
        product = setup_data["product"]

        CartService.clear_cart(customer_id=customer.id)

        try:
            api_client.force_authenticate(user=user)

            # This endpoint adds the product to the Redis cart.
            # It does not create an OrderItem database record.
            url = f"/order/api/v1/order/item/{product.id}/"

            response = api_client.post(
                url,
                {"quantity": 2},
                format="json",
            )

            assert response.status_code == 200, response.data

            cart = CartService.get_cart(customer_id=customer.id)
            assert cart.get(product.id) == 2

            # Check the customer's order-item list endpoint.
            list_url = "/order/api/v1/order/item/"
            list_response = api_client.get(list_url)

            assert list_response.status_code == 200, list_response.data

        finally:
            CartService.clear_cart(customer_id=customer.id)

    def test_order_item_detail_update_delete(
        self,
        api_client,
        setup_data,
    ):
        user = setup_data["user"]
        customer = setup_data["customer"]
        product = setup_data["product"]

        order = Order.objects.create(
            customer=customer,
            status=False,
        )

        order_item = OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
        )

        api_client.force_authenticate(user=user)

        url = f"/order/api/v1/order/item/detail/{order_item.id}/"

        # Retrieve
        response = api_client.get(url)
        assert response.status_code == 200, response.data

        # Update
        response = api_client.put(
            url,
            {"quantity": 3},
            format="json",
        )
        assert response.status_code == 200, response.data

        order_item.refresh_from_db()
        assert order_item.quantity == 3

        # Delete
        response = api_client.delete(url)
        assert response.status_code == 204, getattr(
            response,
            "data",
            None,
        )

        assert not OrderItem.objects.filter(
            pk=order_item.pk
        ).exists()

    def test_shop_order_list(self, api_client, setup_data):
        manager_user = setup_data["manager_user"]
        customer = setup_data["customer"]
        product = setup_data["product"]
        store = setup_data["store"]

        order = Order.objects.create(
            customer=customer,
            status=False,
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
        )

        api_client.force_authenticate(user=manager_user)

        url = "/order/api/v1/shop/order/items/"
        response = api_client.get(url)

        assert response.status_code == 200, response.data

    def test_order_item_api_view(self, api_client, setup_data):
        user = setup_data["user"]
        customer = setup_data["customer"]
        product = setup_data["product"]

        order = Order.objects.create(
            customer=customer,
            status=False,
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=2,
        )

        api_client.force_authenticate(user=user)

        url = "/order/api/v1/order/item/"
        response = api_client.get(url)

        assert response.status_code == 200, response.data

    def test_bill_creation(self, api_client, setup_data):
        user = setup_data["user"]
        customer = setup_data["customer"]
        product = setup_data["product"]
        address = setup_data["address"]

        CartService.clear_cart(customer_id=customer.id)

        try:
            # Bill creation reads products from the Redis cart.
            CartService.add_item(
                customer_id=customer.id,
                product_id=product.id,
                quantity=1,
            )

            api_client.force_authenticate(user=user)

            # The URL parameter is the address ID, not the order ID.
            url = f"/order/api/v1/bill/create/{address.id}/"

            response = api_client.post(
                url,
                {},
                format="json",
            )

            assert response.status_code == 200, response.data

            bill = Bill.objects.get(
                address=address,
                cart__customer=customer,
            )

            assert bill.cart.customer_id == customer.id

            assert OrderItem.objects.filter(
                order=bill.cart,
                product=product,
                quantity=1,
            ).exists()

        finally:
            CartService.clear_cart(customer_id=customer.id)

