from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ItemEstoqueViewSet, MovimentacaoViewSet, UserProfileView # <-- Importe a nova View aqui

router = DefaultRouter()
router.register(r'itens', ItemEstoqueViewSet, basename='itemestoque')
router.register(r'movimentacoes', MovimentacaoViewSet, basename='movimentacao')

urlpatterns = [
    # Suas rotas que já existiam (itens e movimentacoes)
    path('', include(router.urls)),
    
    # A NOVA PORTA DA IDENTIDADE
    path('me/', UserProfileView.as_view(), name='user-profile'), 
]
