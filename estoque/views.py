from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db import transaction
from .serializers import SetorSerializer, SubSetorSerializer, ItemEstoqueSerializer, MovimentacaoSerializer
from .models import Setor, SubSetor, ItemEstoque, Movimentacao, Perfil # Certifique-se de que Perfil está importado aqui

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.is_superuser:
            return Response({
                "username": user.username,
                "cargo": "DONO",
                "empresa": "Administração CapFlow",
            })
            
        try:
            perfil = user.perfil
            return Response({
                "username": user.username,
                "cargo": perfil.cargo,
                "empresa": perfil.empresa.nome_fantasia,
            })
        except:
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


class SubSetorViewSet(viewsets.ModelViewSet):
    serializer_class = SubSetorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return SubSetor.objects.all()
        try:
            perfil = user.perfil
        except:
            return SubSetor.objects.none()

        return SubSetor.objects.filter(setor_pai__empresa=perfil.empresa)


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
            return ItemEstoque.objects.filter(subsetor__setor_pai__empresa=perfil.empresa)
        else:
            return ItemEstoque.objects.filter(subsetor__setor_pai__empresa=perfil.empresa, subsetor__setor_pai__responsavel=user)
    
    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()
            return

        perfil = user.perfil
        subsetor_alvo = serializer.validated_data.get('subsetor')

        if subsetor_alvo.setor_pai.empresa != perfil.empresa:
            raise PermissionDenied("Você não pode cadastrar em um sub-setor de outra empresa.")

        item = serializer.save()

        if item.quantidade_atual > 0:
            Movimentacao.objects.create(
                item=item, tipo='ENTRADA', quantidade_movimentada=item.quantidade_atual,
                observacao="Carga inicializada no cadastro do produto."
            )

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()
            return

        perfil = user.perfil
        subsetor_alvo = serializer.validated_data.get('subsetor', serializer.instance.subsetor)

        if subsetor_alvo.setor_pai.empresa != perfil.empresa:
            raise PermissionDenied("Você não pode mover este produto para um sub-setor de outra empresa.")

        quantidade_anterior = serializer.instance.quantidade_atual
        item = serializer.save()
        diferenca = item.quantidade_atual - quantidade_anterior

        if diferenca > 0:
            Movimentacao.objects.create(item=item, tipo='ENTRADA', quantidade_movimentada=diferenca, observacao="Incremento manual")
        elif diferenca < 0:
            Movimentacao.objects.create(item=item, tipo='SAIDA', quantidade_movimentada=abs(diferenca), observacao="Decremento manual")


class MovimentacaoViewSet(viewsets.ModelViewSet):
    serializer_class = MovimentacaoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Movimentacao.objects.all()
        try:
            return Movimentacao.objects.filter(item__subsetor__setor_pai__empresa=user.perfil.empresa)
        except:
            return Movimentacao.objects.none()

    def perform_create(self, serializer):
        movimentacao = serializer.save()
        item = movimentacao.item
        
        if movimentacao.tipo == 'ENTRADA':
            item.quantidade_atual += movimentacao.quantidade_movimentada
        elif movimentacao.tipo == 'SAIDA':
            item.quantidade_atual -= movimentacao.quantidade_movimentada
            
        item.save()


# 🚨 NOVA VIEWSET DE FUNCIONÁRIOS ADICIONADA 🚨
# 🚨 SUBISTITUA APENAS A SUA FuncionariosViewSet POR ESTA CORRIGIDA 🚨
class FuncionariosViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def list(self, request):
        user = request.user
        perfil_logado = self._get_perfil()

        # Apenas gerentes ou superusuários listam funcionários
        if perfil_logado.cargo != 'GERENTE' and not user.is_superuser:
            raise PermissionDenied("Acesso negado.")

        # 🛠️ CORREÇÃO: Trocado 'user' por 'usuario'
        perfis_empresa = Perfil.objects.filter(empresa=perfil_logado.empresa).select_related('usuario')
        
        dados = []
        for p in perfis_empresa:
            # 🛠️ CORREÇÃO: Trocado p.user por p.usuario
            if p.usuario == user:
                continue
            dados.append({
                "id": p.usuario.id,
                "nome": f"{p.usuario.first_name} {p.usuario.last_name}".strip() or p.usuario.username,
                "email": p.usuario.email,
                "cargo": p.cargo,
                "status": "ATIVO" if p.usuario.is_active else "INATIVO"
            })
        return Response(dados)

    def create(self, request):
        perfil_logado = self._get_perfil()

        # Modificado para permitir que GERENTE também cadastre novos membros
        if perfil_logado.cargo != 'GERENTE' and not request.user.is_superuser:
            raise PermissionDenied("Apenas gerentes podem cadastrar novos funcionários.")

        dados = request.data
        email = dados.get('email')
        nome = dados.get('nome', '')
        senha = dados.get('senha')
        cargo_escolhido = dados.get('cargo', 'OPERADOR')

        if not email or not senha or not nome:
            raise ValidationError({"erro": "Nome, e-mail e senha são obrigatórios."})

        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise ValidationError({"erro": "Este e-mail já está sendo utilizado por outro usuário."})

        # Divide o nome para salvar no padrão do Django (first_name / last_name)
        partes_nome = nome.split(' ', 1)
        primeiro_nome = partes_nome[0]
        sobrenome = partes_nome[1] if len(partes_nome) > 1 else ''

        with transaction.atomic():
            novo_usuario = User.objects.create_user(
                username=email, 
                email=email,
                password=senha,
                first_name=primeiro_nome,
                last_name=sobrenome
            )

            # 🛠️ CORREÇÃO: Alterado de 'user=' para 'usuario=' conforme seu Perfil model
            Perfil.objects.create(
                usuario=novo_usuario,
                empresa=perfil_logado.empresa,
                cargo=cargo_escolhido
            )

        return Response({
            "id": novo_usuario.id,
            "nome": nome,
            "email": email,
            "cargo": cargo_escolhido,
            "status": "ATIVO"
        }, status=201)