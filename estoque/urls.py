from django.urls import path, include
from rest_framework.routers import DefaultRouter
# Adicione SubSetorViewSet aqui!
from .views import SetorViewSet, SubSetorViewSet, ItemEstoqueViewSet, MovimentacaoViewSet, UserProfileView, FuncionariosViewSet

router = DefaultRouter()
router.register(r'setores', SetorViewSet, basename='setor')
router.register(r'subsetores', SubSetorViewSet, basename='subsetor') # Nova Rota
router.register(r'itens', ItemEstoqueViewSet, basename='item')
router.register(r'movimentacoes', MovimentacaoViewSet, basename='movimentacao')
router.register(r'funcionarios', FuncionariosViewSet, basename='funcionarios')


urlpatterns = [
    path('', include(router.urls)),
    path('me/', UserProfileView.as_view(), name='user-profile'), # <-- MUDAMOS AQUI de 'perfil/' para 'me/'
]