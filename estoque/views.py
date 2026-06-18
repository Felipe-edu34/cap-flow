from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Setor, ItemEstoque, Movimentacao
from .serializers import SetorSerializer, ItemEstoqueSerializer, MovimentacaoSerializer

# --- ROTA DE IDENTIDADE ---
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # 1. Se for você (Dono do sistema), passamos um perfil especial
        if user.is_superuser:
            return Response({
                "username": user.username,
                "cargo": "DONO",
                "empresa": "Administração CapFlow",
            })
            
        # 2. Se for um cliente (Gerente ou Funcionário), buscamos o perfil dele
        try:
            perfil = user.perfil
            return Response({
                "username": user.username,
                "cargo": perfil.cargo,
                "empresa": perfil.empresa.nome_fantasia,
            })
        except:
            # 3. Se for um usuário "solto" sem perfil, retorna erro
            return Response({
                "error": "Este usuário não possui um perfil ou empresa vinculada."
            }, status=400)


class SetorViewSet(viewsets.ModelViewSet):
    serializer_class = SetorSerializer
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def _validar_permissao_gerente(self):
        perfil = self._get_perfil()

        if perfil.cargo != 'GERENTE':
            raise PermissionDenied("Apenas gerentes podem cadastrar ou alterar setores.")

        return perfil

    def _validar_responsavel(self, responsavel, empresa):
        if responsavel is None:
            return

        try:
            perfil_responsavel = responsavel.perfil
        except:
            raise PermissionDenied("O responsável informado não possui um perfil vinculado.")

        if perfil_responsavel.empresa != empresa:
            raise PermissionDenied("O responsável precisa pertencer à mesma empresa do gerente.")

    def get_queryset(self):
        user = self.request.user

        if user.is_superuser:
            return Setor.objects.all()

        try:
            perfil = user.perfil
        except:
            return Setor.objects.none()

        if perfil.cargo == 'GERENTE':
            return Setor.objects.filter(empresa=perfil.empresa)

        return Setor.objects.filter(empresa=perfil.empresa, responsavel=user)

    def perform_create(self, serializer):
        perfil = self._validar_permissao_gerente()
        responsavel = serializer.validated_data.get('responsavel')

        self._validar_responsavel(responsavel, perfil.empresa)
        serializer.save(empresa=perfil.empresa)

    def perform_update(self, serializer):
        perfil = self._validar_permissao_gerente()
        responsavel = serializer.validated_data.get('responsavel', serializer.instance.responsavel)

        self._validar_responsavel(responsavel, perfil.empresa)
        serializer.save(empresa=perfil.empresa)

    def perform_destroy(self, instance):
        self._validar_permissao_gerente()
        instance.delete()


class ItemEstoqueViewSet(viewsets.ModelViewSet):
    serializer_class = ItemEstoqueSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            return ItemEstoque.objects.all()
            
        try:
            perfil = user.perfil
        except:
            return ItemEstoque.objects.none()

        if perfil.cargo == 'GERENTE':
            return ItemEstoque.objects.filter(setor__empresa=perfil.empresa)
        else:
            return ItemEstoque.objects.filter(setor__empresa=perfil.empresa, setor__responsavel=user)
    
    def perform_create(self, serializer):
        user = self.request.user
        
        if user.is_superuser:
            serializer.save()
            return

        perfil = user.perfil
        setor_alvo = serializer.validated_data.get('setor')

        if setor_alvo.empresa != perfil.empresa:
            raise PermissionDenied("Operação violada: Você não pode cadastrar um produto em um setor de outra empresa.")

        # Salva o item no estoque
        item = serializer.save()

        # AUTOMATIZAÇÃO: Cria o histórico de entrada inicial se houver estoque cadastrado
        if item.quantidade_atual > 0:
            Movimentacao.objects.create(
                item=item,
                tipo='ENTRADA',
                quantidade_movimentada=item.quantidade_atual,
                observacao="Carga inicializada no cadastro do produto."
            )

    def perform_update(self, serializer):
        user = self.request.user
        
        if user.is_superuser:
            serializer.save()
            return

        perfil = user.perfil
        setor_alvo = serializer.validated_data.get('setor', serializer.instance.setor)

        if setor_alvo.empresa != perfil.empresa:
            raise PermissionDenied("Operação violada: Você não pode mover este produto para um setor de outra empresa.")

        # Guarda o estoque antigo para calcular a diferença de movimentação
        quantidade_anterior = serializer.instance.quantidade_atual

        # Salva as atualizações do produto
        item = serializer.save()

        # AUTOMATIZAÇÃO: Calcula e gera a auditoria baseado na mudança de quantidade
        diferenca = item.quantidade_atual - quantidade_anterior

        if diferenca > 0:
            Movimentacao.objects.create(
                item=item,
                tipo='ENTRADA',
                quantidade_movimentada=diferenca,
                observacao="Incremento manual via painel do gestor."
            )
        elif diferenca < 0:
            Movimentacao.objects.create(
                item=item,
                tipo='SAIDA',
                quantidade_movimentada=abs(diferenca),
                observacao="Decremento/Correção manual via painel do gestor."
            )


class MovimentacaoViewSet(viewsets.ModelViewSet):
    serializer_class = MovimentacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Movimentacao.objects.all()
        try:
            return Movimentacao.objects.filter(item__setor__empresa=user.perfil.empresa)
        except:
            return Movimentacao.objects.none()

    def perform_create(self, serializer):
        # 1. Salva a movimentação nova (criada manualmente ou por outro endpoint)
        movimentacao = serializer.save()
        
        # 2. Pega o item que está sendo modificado
        item = movimentacao.item
        
        # 3. Faz a matemática segura direto no banco
        if movimentacao.tipo == 'ENTRADA':
            item.quantidade_atual += movimentacao.quantidade_movimentada
        elif movimentacao.tipo == 'SAIDA':
            item.quantidade_atual -= movimentacao.quantidade_movimentada
            
        # 4. Salva o novo saldo
        item.save()