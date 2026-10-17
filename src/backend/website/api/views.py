from vendor.api.v1.serializers import StoreSerializer, ProductSerializer,StoreAddressSerializer
from rest_framework import status
from vendor.models import Store,ShopAddress
import random
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from website.models import Product,ProductImages
from vendor.api.v1.serializers import ProductSerializer
from rest_framework.generics import ListAPIView, GenericAPIView
from .pagination import WebsiteShopPaginations,WebsiteRandomProductPaginations
from .serializers import ProductImageSerializer
from rest_framework.permissions import AllowAny
from elasticsearch import Elasticsearch
from ..index import ProductDocument
from django.shortcuts import get_object_or_404
from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
)


class RandomProductsApiView(APIView):
    """
    API view to return a random selection of products.

    Responsibilities
    ----------------
    - GET: Retrieve 5 random products (or fewer if total products < 5).
    - Caches the result for 300 seconds (5 minutes) to reduce database load.

    Attributes
    ----------
    (No class-level attributes; caching uses a fixed key.)

    Methods
    -------
    get(self, request)
        - Handles GET requests.
        - Tries to fetch cached data with key 'random_products_6'.
        - If cache miss: collects all product IDs, selects up to 5 random ones,
          retrieves the corresponding Product queryset, serializes with ProductSerializer,
          stores in cache for 300 seconds.
        - Returns serialized product data as JSON response.

    Usage
    -----
        # Get random products
        GET /api/v1/random-products/ -> returns list of up to 5 random products.

    Notes
    -----
    - The cache key 'random_products_6' suggests a previous version or typo (maybe intended 5).
    - If total products count is less than 5, returns all existing products (random.sample handles it).
    - No authentication required.
    """
    permission_classes =[AllowAny]
    paginations_class = WebsiteRandomProductPaginations
    def get(self, request):
        cache_key = "random_products_6"
        products = cache.get(cache_key)

        if  products is None:

            product_ids = list(
                Product.objects.values_list("id", flat=True)
            )
            random_ids = random.sample(product_ids, min(5, len(product_ids)))

            queryset = Product.objects.filter(
                id__in=random_ids
            ).select_related(
                "category",
                "store",
            )
            serializer = ProductSerializer(queryset, many=True)

            products = serializer.data
            cache.set(cache_key, products, timeout=300)

        return Response(products)


class ProductsFilteringAPIView(ListAPIView):
    
    """
    API view to list products with optional sorting by price.

    Responsibilities
    ----------------
    - GET: Return a list of all products, optionally ordered by price ascending or descending.

    Attributes
    ----------
    serializer_class : ProductSerializer
        - Serializer used to convert Product queryset to JSON.

    Methods
    -------
    get_queryset(self)
        - Returns a queryset of all products.
        - Reads query parameter 'order' from request.GET.
        - If order == 'price_asc': orders by price ascending.
        - If order == 'price_dsc': orders by price descending.
        - Otherwise returns default ordering (database order).
        - Prints the resulting queryset to console for debugging.

    Usage
    -----
        # List all products (default order)
        GET /api/v1/products/

        # List products sorted by price ascending
        GET /api/v1/products/?order=price_asc

        # List products sorted by price descending
        GET /api/v1/products/?order=price_dsc

    Notes
    -----
    - Inherits from ListAPIView, so pagination settings from DRF settings apply.
    - No filtering other than ordering; returns all products.
    - The print statement is for development logging.
    """
    permission_classes =[AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        query_set = Product.objects.all()
        order_param = self.request.query_params.get('order')

        if order_param == 'price_asc':
            query_set = query_set.order_by('price')
            print('this is ', query_set)

        elif order_param == 'price_dsc':
            query_set = query_set.order_by('-price')
            print('this is ', query_set)
        return query_set


# class ProductSearchApi(GenericAPIView):
    
#     def get(self, request):
#         q = request.query_params.get("q")

#         if not q:
#             return Response(
#                 {
#                     "success": False,
#                     "message": "Search query is required."
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         search = ProductDocument.search()

#         search = search.query(
#             "bool",
#             should=[
#                 {
#                     "match": {
#                         "name": {
#                             "query": q,
#                             "boost": 3
#                         }
#                     }
#                 },
#                 {
#                     "match": {
#                         "description": {
#                             "query": q
#                         }
#                     }
#                 }
#             ],
#             minimum_should_match=1
#         )

#         results = search.execute()

#         data = [
#             {
#                 "id": hit.meta.id,
#                 "score": hit.meta.score,
#                 **hit.to_dict()
#             }
#             for hit in results
#         ]

#         return Response(
#             {
#                 "success": True,
#                 "count": len(data),
#                 "results": data
#             },
#             status=status.HTTP_200_OK
#         )




class ProductSearchApi(GenericAPIView):

    def get(self, request):
        q = request.query_params.get("q", "").strip()

        if not q:
            return Response(
                {
                    "success": False,
                    "message": "Search query is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        vector = (
            SearchVector("name", weight="A", config="simple")
            + SearchVector(
                "description",
                weight="B",
                config="simple",
            )
        )

        query = SearchQuery(
            q,
            config="simple",
            search_type="plain",
        )

        products = (
            Product.objects
            .annotate(search_vector=vector)
            .annotate(
                score=SearchRank(
                    vector,
                    query,
                    cover_density=True,
                )
            )
            .filter(search_vector=query)
            .order_by("-score")
        )

        data = [
            {
                "id": product.pk,
                "score": product.score,
                "name": product.name,
                "description": product.description,
            }
            for product in products
        ]

        return Response(
            {
                "success": True,
                "count": len(data),
                "results": data,
            },
            status=status.HTTP_200_OK,
        )


class ListStoreApiView(GenericAPIView):
    """
    API endpoint for retrieving the list of all available stores.

    This endpoint returns a serialized collection of every registered store
    in the system. Each store includes its public information such as
    name, description, image, and other fields defined in the
    StoreSerializer.

    Methods:
        GET:
            Returns a list of all stores.

    Response:
        200 OK:
            [
                {
                    "pk": 1,
                    "name": "Store Name",
                    "description": "Store description",
                    "image": "http://example.com/media/store/image.jpg",
                    ...
                }
            ]
    """
    serializer_class = StoreSerializer
    pagination_class = WebsiteShopPaginations
    permission_classes =[AllowAny]
    queryset = Store.objects.all()
    def get(self, request):
        data =  data = self.get_queryset()
        page = self.paginate_queryset(data)


        if page is not None:

            serializer = self.get_serializer(

                page,

                many=True,

                context={"request": request}

            )

            return self.get_paginated_response(

                serializer.data

            )

        serializer = self.serializer_class(
            instance=data, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductListApiView(GenericAPIView):
    """
    API endpoint for retrieving all products belonging to a specific store.

    This endpoint returns a list of products associated with the provided
    store ID. Each product is serialized using the ProductSerializer and
    includes its public information such as name, price, image, stock,
    and other exposed fields.

    URL Parameters:
        pk (int):
            The primary key of the target store.

    Methods:
        GET:
            Returns all products for the specified store.

    Response:
        200 OK:
            [
                {
                    "pk": 1,
                    "name": "Gaming Mouse",
                    "price": 1200000,
                    "image": "http://example.com/media/products/mouse.jpg",
                    ...
                }
            ]

        404 Not Found:
            Returned if the requested store does not exist (if such validation
            is implemented).
    """
    serializer_class = ProductSerializer
    permission_classes =[AllowAny]
    
    def get_queryset(self, pk):
        return Product.objects.filter(store__pk=pk)

    def get(self, request, pk):
        queryset = self.get_queryset(pk=pk)
        page = self.paginate_queryset(queryset=queryset)
        if page is not None:
            serializer= self.serializer_class(page,
                                              many=True,
                                              context={'request':request})
            return self.get_paginated_response(
                serializer.data
            )
        serializer =  self.serializer_class(queryset,
                                            many=True,
                                            context={'request':request})
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

class ProductDetailAPIView(GenericAPIView):
    """
    API endpoint for retrieving the details of a single product.

    This endpoint returns the complete public information of a specific
    product identified by its primary key. The response is serialized
    using the ProductSerializer.

    URL Parameters:
        pk (int):
            The primary key of the requested product.

    Methods:
        GET:
            Returns the details of the specified product.

    Response:
        200 OK:
            {
                "pk": 1,
                "name": "Gaming Mouse",
                "description": "High precision wireless gaming mouse.",
                "price": 1200000,
                "image": "http://example.com/media/products/mouse.jpg",
                ...
            }

        404 Not Found:
            Returned when the requested product does not exist.
    """
    serializer_class = ProductSerializer
    permission_classes =[AllowAny]
    
    def get_queryset(self, pk):
        return Product.objects.get(pk=pk)

    def get(self, request, pk):
        data = self.get_queryset(pk)
        serializer = self.serializer_class(
            instance=data, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class StoreDetailApiView(GenericAPIView):
    """
    API endpoint for retrieving the details of a specific store.

    This endpoint returns the complete public information of a store
    identified by its primary key. In addition to the fields provided
    by the StoreSerializer, the response includes the store's address
    serialized using the StoreAddressSerializer.

    URL Parameters:
        pk (int):
            The primary key of the requested store.

    Methods:
        GET:
            Returns the details of the specified store along with its
            associated address.

    Response:
        200 OK:
            {
                "pk": 1,
                "name": "Tech Store",
                "description": "Electronics and accessories",
                "image": "http://example.com/media/store/logo.jpg",
                "address": {
                    "state": "Tehran",
                    "street": "Valiasr Street"
                }
            }

        404 Not Found:
            Returned when the requested store or its address does not exist.
    """
    serializer_class = StoreSerializer
    permission_classes =[AllowAny]
    
    def get_address(self, pk):
        return get_object_or_404(ShopAddress, store_id=pk)

    def get(self, request, pk):
        store = get_object_or_404(Store, pk=pk)
        address = self.get_address(pk)
        serializer = self.serializer_class(
            instance=store, context={"request", request})
        response_data = serializer.data
        response_data["address"] = StoreAddressSerializer(address).data
        return Response(response_data, status=status.HTTP_200_OK)




class ListImageProductApiview (GenericAPIView):
    serializer_class = ProductImageSerializer
    
    
    
    def get_queryset(self,pk):
        return ProductImages.objects.filter(product_id=pk)
    
    def get(self,request,pk):
        image_data = self.get_queryset(pk=pk)
        serializer = self.serializer_class(instance=image_data,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    
    
    def post(self,request,pk):
        data = request.data
        product_data = self.get_queryset(pk=pk)
        serializer =  self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.save(product=product_data)
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,status=status.HTTP_404_NOT_FOUND)