from django.urls import path
from order.api.v1 import views

app_name = 'order_api_vi'
urlpatterns = [
    path('orders/', views.OrderListApiView.as_view(), name='order-list'),
   path('order/item/<int:pk>/',views.AddToCartApiView.as_view(), name='order-item-create'),
    path('order/item/list/',views.OrderItemListAPIView.as_view(),name='order-item-list'),
    path('order/item/detail/<int:pk>/',views.OrderItemDetailView.as_view(),name='order_item_detail'),
    path('shop/order/items/',views.ShopOrderListApiView.as_view(),name='shop_order_item'),
    path('order/item/',views.OrderItemApiView.as_view(),name='customer_order_item'),
    path('create/bill/<int:pk>/',views.BillCreationApiView.as_view(),name='bill-creation'),
    path('sessions/cart/',views.CartDetailAPIView.as_view(),name='session-cart'),
    path('session/cart/add/<int:pk>/',view=views.CartAddAPIView.as_view(),name='sessions-cart-add'),
    path('related/order/orderitem/<int:pk>/',view=views.RelatedOrderItemWithOrder.as_view(),name='ralated_orderitem_order'),
    path('bill/create/<int:pk>/',views.BillCreationApiView.as_view(),name='bill-creation'),
    path('bill/list/',view=views.BillListAPIView.as_view(),name='bill-list'),
    path("checkout/",views.CheckoutFromCartApiView.as_view(),name="checkout-from-cart"),


]
