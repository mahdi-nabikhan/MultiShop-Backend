import pytest
from django.urls import reverse, resolve

from vendor.models import User, Manager, Store, ShopAddress

@pytest.mark.django_db
class TestWebsiteURLs:


    @pytest.mark.parametrize(
        "url_name, kwargs",
    [
        ("random-products", None),
        ("product_filter", None),
        ("store-list", None),
        ("product-list", {"pk": 1}),
        ("store-detail", {"pk": 1}),
        ("product-detail", {"pk": 1}),
    ],
)
    def test_urls_resolve(self, url_name, kwargs):
        """Ensure every named URL resolves correctly."""
        if kwargs:
            url = reverse(f"webste_api_v1:{url_name}", kwargs=kwargs)
        else:
            url = reverse(f"webste_api_v1:{url_name}")

        assert resolve(url).url_name == url_name

    def test_random_products_view(self, client):
        """Test random products endpoint."""
        url = reverse("webste_api_v1:random-products")

        response = client.get(url)

        assert response.status_code in [200, 204]

    def test_product_filter_view(self, client):
        """Test filtering endpoint."""
        url = reverse("webste_api_v1:product_filter")

        response = client.get(url)

        assert response.status_code in [200, 204]

    def test_store_list_view(self, client):
        """Test store list endpoint."""
        url = reverse("webste_api_v1:store-list")

        response = client.get(url)

        assert response.status_code in [200, 204]

    def test_store_detail_view(self, client):
        """Test store detail endpoint."""
        user = User.objects.create_user(
            email="manager@test.com",
            password="12345678",
        )

        manager = Manager.objects.create(
            user=user,
            first_name="Test",
            last_name="Manager",
        )

        store = Store.objects.create(
            manager=manager,
            name="Test Store",
            description="Test Description",
        )

        ShopAddress.objects.create(
        store=store,
        street="Valiasr Street",
        city="Tehran",
        state="Tehran",)

        url = reverse(
        "webste_api_v1:store-detail",
        kwargs={"pk": store.pk},
    )

        response = client.get(url)

        assert response.status_code == 200

    def test_store_detail_not_found(self, client):
        """Invalid store ID should return 404."""
        url = reverse(
            "webste_api_v1:store-detail",
            kwargs={"pk": 99999},
        )

        response = client.get(url)

        assert response.status_code == 404



    def test_product_list_view(self, client):
        """Test product list endpoint for a store."""
        user = User.objects.create_user(
        email="manager2@test.com",
        password="12345678",
        )

        manager = Manager.objects.create(
        user=user,
        first_name="Mahdi",
        last_name="Test",
    )

        store = Store.objects.create(
        manager=manager,
        name="Store",
        description="Store Description",
    )

        url = reverse(
        "webste_api_v1:product-list",
        kwargs={"pk": store.pk},
    )

        response = client.get(url)

        assert response.status_code in [200, 204]

