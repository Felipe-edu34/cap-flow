from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ItemEstoque, Movimentacao
from .serializers import ItemEstoqueSerializer, MovimentacaoSerializer

class ItemEstoqueViewSet(viewsets.ModelViewSet):
    serializer_class = ItemEstoqueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ItemEstoque.objects.all()
        return ItemEstoque.objects.filter(setor__responsaveis=user)

class MovimentacaoViewSet(viewsets.ModelViewSet):
    queryset = Movimentacao.objects.all()
    serializer_class = MovimentacaoSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # 1. Salva o histórico e pega quem fez
        movimentacao = serializer.save(usuario=self.request.user)
        
        # 2. Pega o item que está sendo modificado
        item = movimentacao.item
        
        # 3. Faz a matemática segura direto no Banco de Dados
        if movimentacao.tipo == 'ENTRADA':
            item.quantidade_atual += movimentacao.quantidade_movimentada
        elif movimentacao.tipo == 'SAIDA':
            item.quantidade_atual -= movimentacao.quantidade_movimentada
            
        # 4. Salva o novo saldo do item
        item.save()