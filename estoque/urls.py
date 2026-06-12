from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemEstoqueViewSet, MovimentacaoViewSet

router = DefaultRouter()
router.register(r'itens', ItemEstoqueViewSet, basename='itemestoque')
router.register(r'movimentacoes', MovimentacaoViewSet, basename='movimentacao')

urlpatterns = [
    path('', include(router.urls)),
]