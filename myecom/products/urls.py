from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('product/<slug:product_slug>/', views.product_detail, name='product_detail'),  # Change product_slug to slug
    path('product/<int:product_id>/add-review/', views.add_review, name='add_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('cart/add/<int:product_id>/', views.add_to_cart_from_detail, name='add_to_cart_from_detail'),
    path('search/', views.search_products, name='search'),
    path('filter-products/', views.filter_products_ajax, name='filter_products_ajax'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('deals/', views.deals, name='deals'),
    
    path('search/', views.search_products, name='search'),
    path('search/suggestions/', views.live_search_suggestions, name='search_suggestions'),
    
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/products/', views.admin_products, name='admin_products'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/categories/', views.admin_categories, name='admin_categories'),
    path('admin-panel/products/add/', views.admin_add_product, name='admin_add_product'),
    
    # Product Management URLs
    path('admin-panel/products/', views.admin_products, name='admin_products'),
    path('admin-panel/products/add/', views.admin_add_product, name='admin_add_product'),
    path('admin-panel/products/edit/<int:product_id>/', views.admin_edit_product, name='admin_edit_product'),
    path('admin-panel/products/delete/<int:product_id>/', views.admin_delete_product, name='admin_delete_product'),
    
    # Category Management URLs
    path('admin-panel/categories/', views.admin_categories, name='admin_categories'),
    path('admin-panel/categories/add/', views.admin_add_category, name='admin_add_category'),
    path('admin-panel/categories/edit/<int:category_id>/', views.admin_edit_category, name='admin_edit_category'),
    path('admin-panel/categories/delete/<int:category_id>/', views.admin_delete_category, name='admin_delete_category'),
    
    # Admin User Management URLs (Make sure these come BEFORE the admin site URL)
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/add/', views.admin_add_user, name='admin_add_user'),
    path('admin-panel/users/edit/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),
    path('admin-panel/users/delete/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    path('admin-panel/users/check-username/', views.admin_check_username, name='admin_check_username'),
    
    
    # Admin URLs
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/products/', views.admin_products, name='admin_products'),
    path('admin-panel/products/add/', views.admin_add_product, name='admin_add_product'),
    path('admin-panel/products/edit/<int:product_id>/', views.admin_edit_product, name='admin_edit_product'),
    path('admin-panel/products/delete/<int:product_id>/', views.admin_delete_product, name='admin_delete_product'),
    path('admin-panel/orders/', views.admin_orders, name='admin_orders'),
    path('admin-panel/orders/update-status/<int:order_id>/', views.admin_update_order_status, name='admin_update_order_status'),
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/categories/', views.admin_categories, name='admin_categories'),
    path('admin-panel/categories/add/', views.admin_add_category, name='admin_add_category'),
    path('admin-panel/categories/edit/<int:category_id>/', views.admin_edit_category, name='admin_edit_category'),
    path('admin-panel/categories/delete/<int:category_id>/', views.admin_delete_category, name='admin_delete_category'),
    
    # Seller URLs
path('seller/register/', views.seller_register, name='seller_register'),
path('seller/dashboard/', views.seller_dashboard, name='seller_dashboard'),
path('seller/products/', views.seller_products, name='seller_products'),
path('seller/products/add/', views.seller_add_product, name='seller_add_product'),
path('seller/products/edit/<int:product_id>/', views.seller_edit_product, name='seller_edit_product'),
path('seller/products/delete/<int:product_id>/', views.seller_delete_product, name='seller_delete_product'),
path('seller/orders/', views.seller_orders, name='seller_orders'),
path('seller/settings/', views.seller_settings, name='seller_settings'),
path('store/<slug:store_slug>/', views.seller_store, name='seller_store'),
path('product/<slug:slug>/', views.seller_product_detail, name='seller_product_detail'),

    # Admin Seller Management - use a different path to avoid conflicts
    path('admin-panel/sellers/', views.admin_seller_list, name='admin_sellers'),
    path('admin-panel/sellers/<int:seller_id>/', views.admin_seller_detail, name='admin_seller_detail'),
    path('admin-panel/seller-requests/', views.admin_seller_requests, name='admin_seller_requests'),
    path('admin-panel/approve-seller/<int:seller_id>/', views.admin_approve_seller, name='admin_approve_seller'),
    path('admin-panel/reject-seller/<int:seller_id>/', views.admin_reject_seller, name='admin_reject_seller'),
    
    
    
    # In products/urls.py
path('product/<slug:slug>/', views.product_detail, name='product_detail'),
   # ... other URLs ...
    path('products/api/search/', views.search_products_api, name='search_api'),
]