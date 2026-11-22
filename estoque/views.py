from rest_framework import viewsets, status
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.db.models.deletion import ProtectedError
from .serializers import SetorSerializer, SubSetorSerializer, ItemEstoqueSerializer, MovimentacaoSerializer
from .models import Setor, SubSetor, ItemEstoque, Movimentacao, Perfil
from .supabase_auth import (
    supabase_sign_in_with_password,
    decode_supabase_jwt,
    get_or_sync_django_user_from_supabase_payload,
    supabase_admin_create_or_update_user,
    supabase_admin_delete_user,
)


CARGOS_GESTAO = {'GERENTE', 'ADMINISTRADOR', 'GESTOR'}


class SupabaseAuthTokenView(APIView):
    """
    Autentica o usuário diretamente no Supabase Auth (GoTrue), sincroniza o perfil
    no banco de dados e devolve o JWT oficial do Supabase na chave 'token' para
    compatibilidade total com o app mobile e clientes API.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        username_or_email = (request.data.get("username") or request.data.get("email") or "").strip()
        password = request.data.get("password") or ""

        if not username_or_email or not password:
            raise ValidationError({"erro": "Informe o e-mail/usuário e a senha."})

        auth_data = supabase_sign_in_with_password(username_or_email, password)
        access_token = auth_data.get("access_token")
        refresh_token = auth_data.get("refresh_token")

        payload = decode_supabase_jwt(access_token)
        user = get_or_sync_django_user_from_supabase_payload(payload)

        return Response({
            "token": access_token,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
            },
        })


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
        except Perfil.DoesNotExist:
            return Response({
                "error": "Este usuário não possui um perfil ou empresa vinculada."
            }, status=status.HTTP_400_BAD_REQUEST)


class SetorViewSet(viewsets.ModelViewSet):
    serializer_class = SetorSerializer
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except Perfil.DoesNotExist:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def _validar_permissao_gerente(self):
        perfil = self._get_perfil()
        if perfil.cargo not in CARGOS_GESTAO:
            raise PermissionDenied("Apenas gerentes ou gestores podem cadastrar ou alterar setores.")
        return perfil

    def _validar_responsaveis(self, responsaveis, empresa):
        if not responsaveis:
            return
        for resp in responsaveis:
            try:
                perfil_responsavel = resp.perfil
            except Perfil.DoesNotExist:
                raise PermissionDenied(f"O responsável {resp.username} não possui um perfil vinculado.")
            if perfil_responsavel.empresa != empresa:
                raise PermissionDenied(f"O responsável {resp.username} precisa pertencer à mesma empresa do gerente.")

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Setor.objects.all()
        try:
            perfil = user.perfil
        except Perfil.DoesNotExist:
            return Setor.objects.none()

        if perfil.cargo in CARGOS_GESTAO:
            return Setor.objects.filter(empresa=perfil.empresa)

        return Setor.objects.filter(empresa=perfil.empresa, responsaveis=user).distinct()

    def perform_create(self, serializer):
        perfil = self._validar_permissao_gerente()
        responsaveis = serializer.validated_data.get('responsaveis', [])
        self._validar_responsaveis(responsaveis, perfil.empresa)
        serializer.save(empresa=perfil.empresa)

    def perform_update(self, serializer):
        perfil = self._validar_permissao_gerente()
        responsaveis = serializer.validated_data.get('responsaveis', None)
        if responsaveis is not None:
            self._validar_responsaveis(responsaveis, perfil.empresa)
        serializer.save(empresa=perfil.empresa)

    def perform_destroy(self, instance):
        self._validar_permissao_gerente()
        if ItemEstoque.objects.filter(subsetor__setor_pai=instance).exists():
            raise ValidationError({
                "erro": "Não é possível excluir um setor que possui produtos vinculados. Remova ou transfira os produtos antes de excluir."
            })
        try:
            instance.delete()
        except (ProtectedError, IntegrityError):
            raise ValidationError({
                "erro": "Não é possível excluir este setor pois existem registros vinculados a ele."
            })


class SubSetorViewSet(viewsets.ModelViewSet):
    serializer_class = SubSetorSerializer
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except Perfil.DoesNotExist:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def _validar_permissao_gerente(self):
        perfil = self._get_perfil()
        if perfil.cargo not in CARGOS_GESTAO:
            raise PermissionDenied("Apenas gerentes ou gestores podem cadastrar ou alterar sub-setores.")
        return perfil

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return SubSetor.objects.all()
        try:
            perfil = user.perfil
        except Perfil.DoesNotExist:
            return SubSetor.objects.none()

        if perfil.cargo in CARGOS_GESTAO:
            return SubSetor.objects.filter(setor_pai__empresa=perfil.empresa)

        return SubSetor.objects.filter(
            setor_pai__empresa=perfil.empresa,
            setor_pai__responsaveis=user
        ).distinct()

    def perform_create(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        perfil = self._validar_permissao_gerente()
        setor_pai = serializer.validated_data.get('setor_pai')
        if setor_pai.empresa != perfil.empresa:
            raise PermissionDenied("Você não pode criar um sub-setor vinculado a um setor de outra empresa.")
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.is_superuser:
            serializer.save()
            return
        perfil = self._validar_permissao_gerente()
        setor_pai = serializer.validated_data.get('setor_pai', serializer.instance.setor_pai)
        if setor_pai.empresa != perfil.empresa:
            raise PermissionDenied("Você não pode vincular um sub-setor a um setor de outra empresa.")
        serializer.save()

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser:
            self._validar_permissao_gerente()
        if instance.produtos.exists():
            raise ValidationError({
                "erro": "Não é possível excluir um sub-setor que possui produtos vinculados."
            })
        try:
            instance.delete()
        except (ProtectedError, IntegrityError):
            raise ValidationError({
                "erro": "Não é possível excluir este sub-setor pois existem registros vinculados a ele."
            })


class ItemEstoqueViewSet(viewsets.ModelViewSet):
    serializer_class = ItemEstoqueSerializer
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except Perfil.DoesNotExist:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return ItemEstoque.objects.all()
        try:
            perfil = user.perfil
        except Perfil.DoesNotExist:
            return ItemEstoque.objects.none()

        if perfil.cargo in CARGOS_GESTAO:
            return ItemEstoque.objects.filter(subsetor__setor_pai__empresa=perfil.empresa)
        else:
            return ItemEstoque.objects.filter(
                subsetor__setor_pai__empresa=perfil.empresa,
                subsetor__setor_pai__responsaveis=user
            ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        with transaction.atomic():
            if not user.is_superuser:
                perfil = self._get_perfil()
                subsetor_alvo = serializer.validated_data.get('subsetor')

                if subsetor_alvo.setor_pai.empresa != perfil.empresa:
                    raise PermissionDenied("Você não pode cadastrar em um sub-setor de outra empresa.")

                if perfil.cargo not in CARGOS_GESTAO:
                    if not subsetor_alvo.setor_pai.responsaveis.filter(id=user.id).exists():
                        raise PermissionDenied("Você não possui permissão para cadastrar itens neste setor.")

            item = serializer.save()

            if item.quantidade_atual > 0:
                Movimentacao.objects.create(
                    item=item,
                    tipo='ENTRADA',
                    quantidade_movimentada=item.quantidade_atual,
                    observacao="Carga inicializada no cadastro do produto."
                )

    def perform_update(self, serializer):
        user = self.request.user
        with transaction.atomic():
            item_travado = ItemEstoque.objects.select_for_update().get(pk=serializer.instance.pk)
            quantidade_anterior = item_travado.quantidade_atual

            if not user.is_superuser:
                perfil = self._get_perfil()
                subsetor_alvo = serializer.validated_data.get('subsetor', item_travado.subsetor)

                if subsetor_alvo.setor_pai.empresa != perfil.empresa:
                    raise PermissionDenied("Você não pode mover este produto para um sub-setor de outra empresa.")

                if perfil.cargo not in CARGOS_GESTAO:
                    if not subsetor_alvo.setor_pai.responsaveis.filter(id=user.id).exists():
                        raise PermissionDenied("Você não possui permissão para alterar itens neste setor.")

            item = serializer.save()
            diferenca = item.quantidade_atual - quantidade_anterior

            if diferenca > 0:
                Movimentacao.objects.create(
                    item=item,
                    tipo='ENTRADA',
                    quantidade_movimentada=diferenca,
                    observacao="Incremento manual"
                )
            elif diferenca < 0:
                Movimentacao.objects.create(
                    item=item,
                    tipo='SAIDA',
                    quantidade_movimentada=abs(diferenca),
                    observacao="Decremento manual"
                )

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_superuser:
            perfil = self._get_perfil()
            if perfil.cargo not in CARGOS_GESTAO:
                raise PermissionDenied("Apenas gerentes ou gestores podem excluir produtos do estoque.")
        try:
            instance.delete()
        except (ProtectedError, IntegrityError):
            raise ValidationError({
                "erro": "Não é possível excluir este produto pois existem registros protegidos vinculados a ele."
            })


class MovimentacaoViewSet(viewsets.ModelViewSet):
    serializer_class = MovimentacaoSerializer
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except Perfil.DoesNotExist:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Movimentacao.objects.all()
        try:
            perfil = user.perfil
        except Perfil.DoesNotExist:
            return Movimentacao.objects.none()

        if perfil.cargo in CARGOS_GESTAO:
            return Movimentacao.objects.filter(item__subsetor__setor_pai__empresa=perfil.empresa)

        return Movimentacao.objects.filter(
            item__subsetor__setor_pai__empresa=perfil.empresa,
            item__subsetor__setor_pai__responsaveis=user
        ).distinct()

    def perform_create(self, serializer):
        user = self.request.user
        with transaction.atomic():
            item_alvo = serializer.validated_data['item']
            item = ItemEstoque.objects.select_for_update().get(pk=item_alvo.pk)

            if not user.is_superuser:
                perfil = self._get_perfil()
                if item.subsetor.setor_pai.empresa != perfil.empresa:
                    raise PermissionDenied("Você não pode registrar movimentações em um produto de outra empresa.")

                if perfil.cargo not in CARGOS_GESTAO:
                    if not item.subsetor.setor_pai.responsaveis.filter(id=user.id).exists():
                        raise PermissionDenied("Você não tem permissão para movimentar produtos deste setor.")

            tipo = serializer.validated_data['tipo']
            qtd = serializer.validated_data['quantidade_movimentada']
            obs = serializer.validated_data.get('observacao') or ''

            # Deduplicação segura: se o app mobile enviar um POST /movimentacoes/ de carga inicial
            # logo após o POST /itens/ já ter criado a movimentação inicial e o saldo, evita duplicar.
            if (
                tipo == 'ENTRADA'
                and obs.strip().upper() == 'NOVO PRODUTO CADASTRADO'
                and item.quantidade_atual == qtd
                and Movimentacao.objects.filter(
                    item=item,
                    tipo='ENTRADA',
                    quantidade_movimentada=qtd,
                    observacao="Carga inicializada no cadastro do produto."
                ).exists()
            ):
                mov_existente = Movimentacao.objects.filter(
                    item=item,
                    tipo='ENTRADA',
                    quantidade_movimentada=qtd,
                    observacao="Carga inicializada no cadastro do produto."
                ).first()
                serializer.instance = mov_existente
                return

            if tipo == 'SAIDA':
                if item.quantidade_atual < qtd:
                    raise ValidationError({
                        "quantidade_movimentada": (
                            f"Saldo insuficiente em estoque. Disponível: {item.quantidade_atual}, "
                            f"solicitado para saída: {qtd}."
                        )
                    })
                item.quantidade_atual -= qtd
            elif tipo == 'ENTRADA':
                item.quantidade_atual += qtd

            item.save(update_fields=['quantidade_atual'])
            serializer.save(item=item)

    def update(self, request, *args, **kwargs):
        raise ValidationError({
            "erro": "Registros históricos de movimentação são imutáveis e não podem ser alterados."
        })

    def partial_update(self, request, *args, **kwargs):
        raise ValidationError({
            "erro": "Registros históricos de movimentação são imutáveis e não podem ser alterados."
        })

    def destroy(self, request, *args, **kwargs):
        raise ValidationError({
            "erro": "Registros históricos de movimentação são imutáveis e não podem ser excluídos para preservar a auditoria."
        })


class FuncionariosViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_perfil(self):
        try:
            return self.request.user.perfil
        except Perfil.DoesNotExist:
            raise PermissionDenied("Este usuário não possui um perfil vinculado.")

    def _validar_gestor(self, request):
        perfil_logado = self._get_perfil()
        if perfil_logado.cargo not in CARGOS_GESTAO and not request.user.is_superuser:
            raise PermissionDenied("Apenas gerentes ou gestores podem gerenciar funcionários.")
        return perfil_logado

    def _get_funcionario_empresa(self, pk, empresa):
        try:
            perfil_alvo = Perfil.objects.select_related('usuario').get(
                usuario_id=pk,
                empresa=empresa
            )
            return perfil_alvo
        except Perfil.DoesNotExist:
            raise NotFound("Funcionário não encontrado nesta empresa.")

    def _serializar_funcionario(self, perfil_obj):
        u = perfil_obj.usuario
        return {
            "id": u.id,
            "nome": f"{u.first_name} {u.last_name}".strip() or u.username,
            "email": u.email,
            "cargo": perfil_obj.cargo,
            "status": "ATIVO" if u.is_active else "INATIVO",
        }

    def list(self, request):
        user = request.user
        perfil_logado = self._validar_gestor(request)

        perfis_empresa = Perfil.objects.filter(empresa=perfil_logado.empresa).select_related('usuario')

        dados = []
        for p in perfis_empresa:
            if p.usuario == user:
                continue
            dados.append(self._serializar_funcionario(p))
        return Response(dados)

    def retrieve(self, request, pk=None):
        perfil_logado = self._validar_gestor(request)
        perfil_alvo = self._get_funcionario_empresa(pk, perfil_logado.empresa)
        return Response(self._serializar_funcionario(perfil_alvo))

    def create(self, request):
        perfil_logado = self._validar_gestor(request)

        dados = request.data
        email = (dados.get('email') or '').strip()
        nome = (dados.get('nome') or '').strip()
        senha = dados.get('senha')
        cargo_escolhido = dados.get('cargo', 'OPERADOR')

        if not email or not senha or not nome:
            raise ValidationError({"erro": "Nome, e-mail e senha são obrigatórios."})

        if len(email) > 150 or len(nome) > 150:
            raise ValidationError({"erro": "Nome ou e-mail excede o limite máximo de 150 caracteres."})

        cargos_validos = {c[0] for c in Perfil.TIPOS_CARGO}
        if cargo_escolhido not in cargos_validos:
            raise ValidationError({"cargo": f"Cargo inválido. Opções válidas: {', '.join(sorted(cargos_validos))}."})

        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise ValidationError({"erro": "Este e-mail já está sendo utilizado por outro usuário."})

        partes_nome = nome.split(' ', 1)
        primeiro_nome = partes_nome[0][:150]
        sobrenome = (partes_nome[1] if len(partes_nome) > 1 else '')[:150]

        with transaction.atomic():
            novo_usuario = User.objects.create_user(
                username=email,
                email=email,
                password=senha,
                first_name=primeiro_nome,
                last_name=sobrenome
            )

            novo_perfil = Perfil.objects.create(
                usuario=novo_usuario,
                empresa=perfil_logado.empresa,
                cargo=cargo_escolhido
            )

            # Provisiona automaticamente a conta no Supabase Auth (GoTrue)
            supabase_admin_create_or_update_user(
                email=email,
                password=senha,
                user_metadata={
                    "nome": nome,
                    "cargo": cargo_escolhido,
                    "empresa": perfil_logado.empresa.nome_fantasia,
                },
            )

        return Response(self._serializar_funcionario(novo_perfil), status=status.HTTP_201_CREATED)

    def _atualizar_funcionario(self, request, pk=None):
        perfil_logado = self._validar_gestor(request)
        perfil_alvo = self._get_funcionario_empresa(pk, perfil_logado.empresa)
        usuario_alvo = perfil_alvo.usuario
        dados = request.data

        with transaction.atomic():
            if 'nome' in dados:
                nome = (dados.get('nome') or '').strip()
                if not nome:
                    raise ValidationError({"nome": "O nome não pode ser vazio."})
                partes_nome = nome.split(' ', 1)
                usuario_alvo.first_name = partes_nome[0][:150]
                usuario_alvo.last_name = (partes_nome[1] if len(partes_nome) > 1 else '')[:150]

            if 'email' in dados:
                novo_email = (dados.get('email') or '').strip()
                if not novo_email or len(novo_email) > 150:
                    raise ValidationError({"email": "E-mail inválido ou excede 150 caracteres."})
                if User.objects.exclude(pk=usuario_alvo.pk).filter(email=novo_email).exists() or \
                   User.objects.exclude(pk=usuario_alvo.pk).filter(username=novo_email).exists():
                    raise ValidationError({"email": "Este e-mail já está sendo utilizado por outro usuário."})
                usuario_alvo.email = novo_email
                usuario_alvo.username = novo_email

            if 'senha' in dados and dados.get('senha'):
                usuario_alvo.set_password(dados['senha'])

            if 'status' in dados:
                status_val = (dados.get('status') or '').upper()
                if status_val not in {'ATIVO', 'INATIVO'}:
                    raise ValidationError({"status": "Status inválido. Use 'ATIVO' ou 'INATIVO'."})
                usuario_alvo.is_active = (status_val == 'ATIVO')

            if 'cargo' in dados:
                novo_cargo = dados.get('cargo')
                cargos_validos = {c[0] for c in Perfil.TIPOS_CARGO}
                if novo_cargo not in cargos_validos:
                    raise ValidationError({"cargo": "Cargo inválido."})
                perfil_alvo.cargo = novo_cargo
                perfil_alvo.save(update_fields=['cargo'])

            usuario_alvo.save()

            # Sincroniza alterações com o Supabase Auth
            supabase_admin_create_or_update_user(
                email=usuario_alvo.email,
                password=dados.get('senha') if dados.get('senha') else None,
                user_metadata={
                    "nome": f"{usuario_alvo.first_name} {usuario_alvo.last_name}".strip(),
                    "cargo": perfil_alvo.cargo,
                    "empresa": perfil_logado.empresa.nome_fantasia,
                },
                ban_user=(not usuario_alvo.is_active),
            )

        return Response(self._serializar_funcionario(perfil_alvo))

    def update(self, request, pk=None):
        return self._atualizar_funcionario(request, pk=pk)

    def partial_update(self, request, pk=None):
        return self._atualizar_funcionario(request, pk=pk)

    def destroy(self, request, pk=None):
        perfil_logado = self._validar_gestor(request)
        perfil_alvo = self._get_funcionario_empresa(pk, perfil_logado.empresa)
        usuario_alvo = perfil_alvo.usuario
        email_alvo = usuario_alvo.email

        if usuario_alvo == request.user:
            raise ValidationError({"erro": "Você não pode excluir a sua própria conta de usuário."})

        try:
            with transaction.atomic():
                usuario_alvo.delete()
                if email_alvo:
                    supabase_admin_delete_user(email_alvo)
        except (ProtectedError, IntegrityError):
            raise ValidationError({
                "erro": "Não é possível excluir este funcionário pois existem registros protegidos vinculados a ele."
            })

        return Response(status=status.HTTP_204_NO_CONTENT)