from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ItemEstoque, Movimentacao
from .serializers import ItemEstoqueSerializer, MovimentacaoSerializer

class ItemEstoqueViewSet(viewsets.ModelViewSet):
    serializer_class = ItemEstoqueSerializer
    # Garante que só quem está logado no app pode acessar
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Se for o patrão/admin, ele vê tudo!
        if user.is_staff:
            return ItemEstoque.objects.all()
        
        # Se for funcionário, o Django busca os setores onde ele foi colocado como responsável
        return ItemEstoque.objects.filter(setor__responsaveis=user)

class MovimentacaoViewSet(viewsets.ModelViewSet):
    queryset = Movimentacao.objects.all()
    serializer_class = MovimentacaoSerializer
    permission_classes = [IsAuthenticated]

    # Quando o funcionário registrar uma movimentação no celular, salvamos automaticamente o ID dele
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)