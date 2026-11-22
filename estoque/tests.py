from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import (
    Empresa,
    Perfil,
    Setor,
    SubSetor,
    ItemEstoque,
    Movimentacao,
    Funcionario,
)


class EstoqueModelsCompleteTest(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nome_fantasia="CapFlow Bonelaria")
        self.user = User.objects.create_user(username="operador1", password="password123")
        self.perfil = Perfil.objects.create(usuario=self.user, empresa=self.empresa)
        self.setor = Setor.objects.create(empresa=self.empresa, nome="Costura")
        self.subsetor = SubSetor.objects.create(setor_pai=self.setor, nome="Bancada 1")

    def test_empresa_fields_and_metadata(self):
        self.assertEqual(str(self.empresa), "CapFlow Bonelaria")
        self.assertIsNotNone(self.empresa.criado_em)
        self.assertIsNone(self.empresa.cnpj)

        f_nome = Empresa._meta.get_field("nome_fantasia")
        self.assertEqual(f_nome.max_length, 150)

        f_cnpj = Empresa._meta.get_field("cnpj")
        self.assertEqual(f_cnpj.max_length, 20)
        self.assertTrue(f_cnpj.blank)
        self.assertTrue(f_cnpj.null)

        f_criado = Empresa._meta.get_field("criado_em")
        self.assertTrue(f_criado.auto_now_add)

    def test_perfil_fields_choices_and_defaults(self):
        self.assertEqual(self.perfil.cargo, "OPERADOR")
        self.assertEqual(
            str(self.perfil),
            "operador1 | OPERADOR (CapFlow Bonelaria)",
        )
        self.assertEqual(self.user.perfil, self.perfil)

        expected_choices = (
            ("ADMINISTRADOR", "Administrador"),
            ("GESTOR", "Gestor"),
            ("OPERADOR", "Operador"),
            ("GERENTE", "Gerente"),
        )
        self.assertEqual(Perfil.TIPOS_CARGO, expected_choices)

        f_cargo = Perfil._meta.get_field("cargo")
        self.assertEqual(f_cargo.max_length, 20)
        self.assertEqual(f_cargo.default, "OPERADOR")
        self.assertEqual(tuple(f_cargo.choices), expected_choices)

        f_usuario = Perfil._meta.get_field("usuario")
        self.assertEqual(f_usuario.remote_field.related_name, "perfil")

    def test_setor_and_subsetor_fields_and_relations(self):
        self.assertEqual(str(self.setor), "Costura - CapFlow Bonelaria")
        self.assertEqual(str(self.subsetor), "Bancada 1 (pertence a: Costura)")

        f_setor_nome = Setor._meta.get_field("nome")
        self.assertEqual(f_setor_nome.max_length, 100)

        f_resp = Setor._meta.get_field("responsaveis")
        self.assertTrue(f_resp.blank)
        self.assertEqual(f_resp.remote_field.related_name, "setores_gerenciados")

        self.setor.responsaveis.add(self.user)
        self.assertIn(self.setor, self.user.setores_gerenciados.all())

        f_sub_nome = SubSetor._meta.get_field("nome")
        self.assertEqual(f_sub_nome.max_length, 100)

        f_setor_pai = SubSetor._meta.get_field("setor_pai")
        self.assertEqual(f_setor_pai.remote_field.related_name, "subsetores")
        self.assertIn(self.subsetor, self.setor.subsetores.all())

    def test_item_estoque_defaults_and_metadata(self):
        item = ItemEstoque.objects.create(
            nome="Aba Curva",
            subsetor=self.subsetor,
        )
        self.assertEqual(str(item), "Aba Curva")
        self.assertEqual(item.quantidade_atual, 0)
        self.assertEqual(item.unidade_medida, "UN")
        self.assertEqual(item.estoque_minimo, 0)
        self.assertIsNone(item.gerente)
        self.assertFalse(bool(item.imagem))

        self.assertEqual(ItemEstoque._meta.get_field("nome").max_length, 100)
        self.assertEqual(ItemEstoque._meta.get_field("quantidade_atual").default, 0)

        f_un = ItemEstoque._meta.get_field("unidade_medida")
        self.assertEqual(f_un.max_length, 10)
        self.assertEqual(f_un.default, "UN")

        self.assertEqual(ItemEstoque._meta.get_field("estoque_minimo").default, 0)
        self.assertEqual(
            ItemEstoque._meta.get_field("subsetor").remote_field.related_name,
            "produtos",
        )

        f_gerente = ItemEstoque._meta.get_field("gerente")
        self.assertTrue(f_gerente.null)
        self.assertTrue(f_gerente.blank)

        f_img = ItemEstoque._meta.get_field("imagem")
        self.assertEqual(f_img.upload_to, "produtos/")
        self.assertTrue(f_img.null)
        self.assertTrue(f_img.blank)

    def test_movimentacao_fields_choices_and_ordering(self):
        item = ItemEstoque.objects.create(
            nome="Linha Branca",
            quantidade_atual=10,
            subsetor=self.subsetor,
        )
        mov1 = Movimentacao.objects.create(
            item=item,
            tipo="ENTRADA",
            quantidade_movimentada=10,
            observacao="Inicial",
        )
        mov2 = Movimentacao.objects.create(
            item=item,
            tipo="SAIDA",
            quantidade_movimentada=3,
        )
        self.assertEqual(str(mov1), "ENTRADA - Linha Branca (10)")
        self.assertEqual(str(mov2), "SAIDA - Linha Branca (3)")
        self.assertIsNotNone(mov1.data_movimentacao)

        expected_mov_choices = (
            ("ENTRADA", "Entrada"),
            ("SAIDA", "Saída"),
        )
        self.assertEqual(Movimentacao.TIPOS_MOV, expected_mov_choices)
        self.assertEqual(Movimentacao._meta.ordering, ["-data_movimentacao"])

        f_item = Movimentacao._meta.get_field("item")
        self.assertEqual(f_item.remote_field.related_name, "movimentacoes")

        f_tipo = Movimentacao._meta.get_field("tipo")
        self.assertEqual(f_tipo.max_length, 10)
        self.assertEqual(tuple(f_tipo.choices), expected_mov_choices)

        self.assertEqual(Movimentacao._meta.get_field("quantidade_movimentada").default, 0)
        self.assertTrue(Movimentacao._meta.get_field("data_movimentacao").auto_now_add)

        f_obs = Movimentacao._meta.get_field("observacao")
        self.assertEqual(f_obs.max_length, 255)
        self.assertTrue(f_obs.blank)
        self.assertTrue(f_obs.null)

    def test_funcionario_fields_choices_and_defaults(self):
        func = Funcionario.objects.create(
            nome="Carlos Silva",
            email="carlos@capflow.com",
            senha="hash_password",
        )
        self.assertEqual(str(func), "Carlos Silva")
        self.assertEqual(func.cargo, "OPERADOR")
        self.assertEqual(func.status, "ATIVO")
        self.assertIsNotNone(func.criado_em)

        expected_cargos = [
            ("ADMINISTRADOR", "Administrador"),
            ("GESTOR", "Gestor"),
            ("OPERADOR", "Operador"),
        ]
        expected_status = [
            ("ATIVO", "Ativo"),
            ("INATIVO", "Inativo"),
        ]
        self.assertEqual(Funcionario.CARGOS_CHOICES, expected_cargos)
        self.assertEqual(Funcionario.STATUS_CHOICES, expected_status)

        self.assertEqual(Funcionario._meta.get_field("nome").max_length, 255)
        self.assertTrue(Funcionario._meta.get_field("email").unique)
        self.assertEqual(Funcionario._meta.get_field("senha").max_length, 255)

        f_cargo = Funcionario._meta.get_field("cargo")
        self.assertEqual(f_cargo.max_length, 50)
        self.assertEqual(f_cargo.default, "OPERADOR")
        self.assertEqual(f_cargo.choices, expected_cargos)

        f_status = Funcionario._meta.get_field("status")
        self.assertEqual(f_status.max_length, 20)
        self.assertEqual(f_status.default, "ATIVO")
        self.assertEqual(f_status.choices, expected_status)

        self.assertTrue(Funcionario._meta.get_field("criado_em").auto_now_add)


class CapflowCRUDAuditAPITest(APITestCase):
    """
    Suíte completa de testes de integração CRUD (POST, PUT, PATCH, DELETE),
    Regras de Movimentação/Saída de Estoque e Isolamento Multi-Tenant no PostgreSQL.
    """

    def setUp(self):
        # Empresa A e seus usuários
        self.empresa_a = Empresa.objects.create(nome_fantasia="Bonelaria Alpha", cnpj="11.111.111/0001-11")
        self.gerente_a = User.objects.create_user(username="gerente_a", email="gerente@alpha.com", password="123")
        self.perfil_gerente_a = Perfil.objects.create(
            usuario=self.gerente_a, empresa=self.empresa_a, cargo="GERENTE"
        )

        self.operador_a = User.objects.create_user(username="operador_a", email="op@alpha.com", password="123")
        self.perfil_operador_a = Perfil.objects.create(
            usuario=self.operador_a, empresa=self.empresa_a, cargo="OPERADOR"
        )

        self.setor_a = Setor.objects.create(empresa=self.empresa_a, nome="Costura Alpha")
        self.setor_a.responsaveis.add(self.operador_a)
        self.subsetor_a = SubSetor.objects.create(setor_pai=self.setor_a, nome="Máquinas Retas")

        # Empresa B (Concorrente / Outro Tenant)
        self.empresa_b = Empresa.objects.create(nome_fantasia="Bonelaria Beta", cnpj="22.222.222/0001-22")
        self.gerente_b = User.objects.create_user(username="gerente_b", email="gerente@beta.com", password="123")
        self.perfil_gerente_b = Perfil.objects.create(
            usuario=self.gerente_b, empresa=self.empresa_b, cargo="GERENTE"
        )
        self.setor_b = Setor.objects.create(empresa=self.empresa_b, nome="Acabamento Beta")
        self.subsetor_b = SubSetor.objects.create(setor_pai=self.setor_b, nome="Bancada Beta")
        self.item_b = ItemEstoque.objects.create(
            nome="Tecido Beta",
            quantidade_atual=50,
            unidade_medida="M",
            estoque_minimo=10,
            subsetor=self.subsetor_b,
        )

        self.client.force_authenticate(user=self.gerente_a)

    # =========================================================================
    # 1. CICLO DE VIDA DE SETOR E SUB-SETOR (POST, PATCH, PUT, DELETE)
    # =========================================================================
    def test_crud_setor_e_bloqueio_exclusao_com_produtos(self):
        # 1. Criação (POST) -> deve vincular automaticamente à Empresa A
        res_post = self.client.post(
            "/api/setores/",
            {"nome": "Corte e Estamparia", "responsaveis": [self.operador_a.id]},
            format="json",
        )
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        setor_id = res_post.data["id"]
        self.assertEqual(res_post.data["empresa"], self.empresa_a.id)
        self.assertIn("operador_a", res_post.data["responsaveis_nomes"])

        # 2. Alteração parcial (PATCH) e completa (PUT)
        res_patch = self.client.patch(
            f"/api/setores/{setor_id}/",
            {"nome": "Corte Laser"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["nome"], "Corte Laser")

        res_put = self.client.put(
            f"/api/setores/{setor_id}/",
            {"nome": "Corte Industrial", "responsaveis": []},
            format="json",
        )
        self.assertEqual(res_put.status_code, status.HTTP_200_OK)
        self.assertEqual(res_put.data["nome"], "Corte Industrial")
        self.assertEqual(res_put.data["responsaveis"], [])

        # 3. Criar SubSetor e Produto vinculado para testar bloqueio de exclusão
        res_sub = self.client.post(
            "/api/subsetores/",
            {"nome": "Mesa de Corte 1", "setor_pai": setor_id},
            format="json",
        )
        self.assertEqual(res_sub.status_code, status.HTTP_201_CREATED)
        sub_id = res_sub.data["id"]

        item = ItemEstoque.objects.create(
            nome="Brim Pesado",
            quantidade_atual=20,
            subsetor_id=sub_id,
        )

        # Tentativa de excluir SubSetor com produto vinculado -> deve retornar 400 amigável (não 500)
        res_del_sub_bloqueado = self.client.delete(f"/api/subsetores/{sub_id}/")
        self.assertEqual(res_del_sub_bloqueado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("erro", res_del_sub_bloqueado.data)

        # Tentativa de excluir Setor com produto vinculado -> deve retornar 400 amigável
        res_del_setor_bloqueado = self.client.delete(f"/api/setores/{setor_id}/")
        self.assertEqual(res_del_setor_bloqueado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("erro", res_del_setor_bloqueado.data)

        # 4. Após remover o produto, a exclusão do SubSetor e do Setor deve ser permitida (204)
        item.delete()
        res_del_sub_livre = self.client.delete(f"/api/subsetores/{sub_id}/")
        self.assertEqual(res_del_sub_livre.status_code, status.HTTP_204_NO_CONTENT)

        res_del_setor_livre = self.client.delete(f"/api/setores/{setor_id}/")
        self.assertEqual(res_del_setor_livre.status_code, status.HTTP_204_NO_CONTENT)

    # =========================================================================
    # 2. CICLO DE VIDA DE FUNCIONÁRIO (POST, PATCH, PUT, DELETE)
    # =========================================================================
    def test_crud_completo_funcionario(self):
        # 1. Criação (POST)
        payload = {
            "nome": "Mariana Costa",
            "email": "mariana@alpha.com",
            "senha": "senhaSegura123",
            "cargo": "GESTOR",
        }
        res_post = self.client.post("/api/funcionarios/", payload, format="json")
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        func_id = res_post.data["id"]
        self.assertEqual(res_post.data["nome"], "Mariana Costa")
        self.assertEqual(res_post.data["cargo"], "GESTOR")
        self.assertEqual(res_post.data["status"], "ATIVO")

        # Bloqueio de e-mail duplicado
        res_dup = self.client.post("/api/funcionarios/", payload, format="json")
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Edição parcial (PATCH) -> alterar cargo, nome e status para INATIVO
        res_patch = self.client.patch(
            f"/api/funcionarios/{func_id}/",
            {"nome": "Mariana Costa Silva", "cargo": "OPERADOR", "status": "INATIVO"},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["nome"], "Mariana Costa Silva")
        self.assertEqual(res_patch.data["cargo"], "OPERADOR")
        self.assertEqual(res_patch.data["status"], "INATIVO")

        # 3. Exclusão (DELETE)
        res_del = self.client.delete(f"/api/funcionarios/{func_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=func_id).exists())

        # Bloqueio de auto-exclusão do próprio gerente logado
        res_self_del = self.client.delete(f"/api/funcionarios/{self.gerente_a.id}/")
        self.assertEqual(res_self_del.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # 3. CICLO DE VIDA DE PRODUTO / ITEM DE ESTOQUE (POST, PATCH, DELETE)
    # =========================================================================
    def test_crud_produto_sem_duplicidade_de_movimentacao(self):
        # 1. Criação (POST) com saldo inicial 30 -> deve gerar EXATAMENTE 1 movimentação
        res_post = self.client.post(
            "/api/itens/",
            {
                "nome": "Aba Plástica Preta",
                "quantidade_atual": 30,
                "unidade_medida": "UN",
                "estoque_minimo": 10,
                "subsetor": self.subsetor_a.id,
            },
            format="json",
        )
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        item_id = res_post.data["id"]

        movs_iniciais = Movimentacao.objects.filter(item_id=item_id)
        self.assertEqual(movs_iniciais.count(), 1)
        self.assertEqual(movs_iniciais.first().tipo, "ENTRADA")
        self.assertEqual(movs_iniciais.first().quantidade_movimentada, 30)

        # 2. Edição de quantidade via PATCH (de 30 para 25 -> baixa de 5 unidades)
        # Deve gerar EXATAMENTE 1 nova movimentação de SAIDA (total = 2), sem duplicar pelo signal!
        res_patch = self.client.patch(
            f"/api/itens/{item_id}/",
            {"quantidade_atual": 25},
            format="json",
        )
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data["quantidade_atual"], 25)

        todas_movs = Movimentacao.objects.filter(item_id=item_id)
        self.assertEqual(todas_movs.count(), 2)
        mov_saida = todas_movs.filter(tipo="SAIDA").first()
        self.assertIsNotNone(mov_saida)
        self.assertEqual(mov_saida.quantidade_movimentada, 5)

        # 3. Edição apenas de nome (sem mudar quantidade) -> NÃO deve criar movimentação
        res_patch_nome = self.client.patch(
            f"/api/itens/{item_id}/",
            {"nome": "Aba Plástica Preta Reforçada"},
            format="json",
        )
        self.assertEqual(res_patch_nome.status_code, status.HTTP_200_OK)
        self.assertEqual(Movimentacao.objects.filter(item_id=item_id).count(), 2)

        # 4. Bloqueio de quantidade negativa via PATCH
        res_patch_neg = self.client.patch(
            f"/api/itens/{item_id}/",
            {"quantidade_atual": -5},
            format="json",
        )
        self.assertEqual(res_patch_neg.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. Exclusão (DELETE)
        res_del = self.client.delete(f"/api/itens/{item_id}/")
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ItemEstoque.objects.filter(pk=item_id).exists())

    # =========================================================================
    # 4. AUDITORIA DE ENTRADAS, SAÍDAS DE ESTOQUE E BLOQUEIO DE SALDO NEGATIVO
    # =========================================================================
    def test_movimentacoes_entrada_saida_e_bloqueio_saldo_insuficiente(self):
        item = ItemEstoque.objects.create(
            nome="Fecho Velcro",
            quantidade_atual=15,
            unidade_medida="UN",
            estoque_minimo=5,
            subsetor=self.subsetor_a,
        )

        # 1. Registrar ENTRADA de 10 unidades (testando alias 'quantidade' usado pelo app mobile)
        res_entrada = self.client.post(
            "/api/movimentacoes/",
            {"item": item.id, "tipo": "ENTRADA", "quantidade": 10, "observacao": "Compra fornecedor"},
            format="json",
        )
        self.assertEqual(res_entrada.status_code, status.HTTP_201_CREATED)
        item.refresh_from_db()
        self.assertEqual(item.quantidade_atual, 25)
        self.assertEqual(Movimentacao.objects.filter(item=item).count(), 1)

        # 2. Registrar SAIDA válida de 8 unidades (usando 'quantidade_movimentada')
        res_saida = self.client.post(
            "/api/movimentacoes/",
            {"item": item.id, "tipo": "SAIDA", "quantidade_movimentada": 8, "observacao": "Baixa produção"},
            format="json",
        )
        self.assertEqual(res_saida.status_code, status.HTTP_201_CREATED)
        item.refresh_from_db()
        self.assertEqual(item.quantidade_atual, 17)
        # Garante que não houve duplicidade (1 entrada + 1 saída = 2 registros)
        self.assertEqual(Movimentacao.objects.filter(item=item).count(), 2)

        # 3. Bloqueio de SAIDA maior que o saldo disponível (solicitar 20 tendo 17)
        res_saida_excesso = self.client.post(
            "/api/movimentacoes/",
            {"item": item.id, "tipo": "SAIDA", "quantidade_movimentada": 20},
            format="json",
        )
        self.assertEqual(res_saida_excesso.status_code, status.HTTP_400_BAD_REQUEST)
        item.refresh_from_db()
        self.assertEqual(item.quantidade_atual, 17)
        self.assertEqual(Movimentacao.objects.filter(item=item).count(), 2)

        # 4. Bloqueio de quantidade zero ou negativa na movimentação
        res_qtd_zero = self.client.post(
            "/api/movimentacoes/",
            {"item": item.id, "tipo": "SAIDA", "quantidade_movimentada": 0},
            format="json",
        )
        self.assertEqual(res_qtd_zero.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. Imutabilidade do histórico (bloqueio de DELETE e PATCH em movimentação)
        mov_id = res_saida.data["id"]
        res_del_mov = self.client.delete(f"/api/movimentacoes/{mov_id}/")
        self.assertEqual(res_del_mov.status_code, status.HTTP_400_BAD_REQUEST)

        res_patch_mov = self.client.patch(
            f"/api/movimentacoes/{mov_id}/",
            {"quantidade_movimentada": 1},
            format="json",
        )
        self.assertEqual(res_patch_mov.status_code, status.HTTP_400_BAD_REQUEST)

    # =========================================================================
    # 5. ISOLAMENTO MULTI-TENANT (EMPRESA A NÃO ACESSA/ALTERA/EXCLUI EMPRESA B)
    # =========================================================================
    def test_isolamento_multi_tenant_entre_empresas(self):
        # Gerente A não pode ver, editar ou excluir Setor da Empresa B
        self.assertEqual(
            self.client.patch(f"/api/setores/{self.setor_b.id}/", {"nome": "Hack"}).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f"/api/setores/{self.setor_b.id}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # Gerente A não pode criar SubSetor apontando para Setor da Empresa B
        res_sub_cross = self.client.post(
            "/api/subsetores/",
            {"nome": "Sub Invasor", "setor_pai": self.setor_b.id},
            format="json",
        )
        self.assertEqual(res_sub_cross.status_code, status.HTTP_403_FORBIDDEN)

        # Gerente A não pode editar nem excluir SubSetor da Empresa B
        self.assertEqual(
            self.client.patch(f"/api/subsetores/{self.subsetor_b.id}/", {"nome": "Hack"}).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f"/api/subsetores/{self.subsetor_b.id}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

        # Gerente A não pode criar produto em SubSetor da Empresa B
        res_item_cross = self.client.post(
            "/api/itens/",
            {"nome": "Produto Invasor", "quantidade_atual": 10, "subsetor": self.subsetor_b.id},
            format="json",
        )
        self.assertEqual(res_item_cross.status_code, status.HTTP_403_FORBIDDEN)

        # Gerente A não pode editar, excluir ou movimentar Produto da Empresa B
        self.assertEqual(
            self.client.patch(f"/api/itens/{self.item_b.id}/", {"quantidade_atual": 0}).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f"/api/itens/{self.item_b.id}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        res_mov_cross = self.client.post(
            "/api/movimentacoes/",
            {"item": self.item_b.id, "tipo": "SAIDA", "quantidade_movimentada": 5},
            format="json",
        )
        self.assertEqual(res_mov_cross.status_code, status.HTTP_403_FORBIDDEN)
        self.item_b.refresh_from_db()
        self.assertEqual(self.item_b.quantidade_atual, 50)

        # Gerente A não pode editar nem excluir Funcionário da Empresa B
        self.assertEqual(
            self.client.patch(
                f"/api/funcionarios/{self.gerente_b.id}/", {"nome": "Hack"}
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.delete(f"/api/funcionarios/{self.gerente_b.id}/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # =========================================================================
    # 6. AUTENTICAÇÃO VIA SUPABASE AUTH (JWT + AUTO-PROVISIONAMENTO DE PERFIL)
    # =========================================================================
    def test_supabase_jwt_authentication_and_sync(self):
        from unittest.mock import patch
        from rest_framework.test import APIClient

        fake_jwt = "eyJhbGciOiJFUzI1NiJ9.eyJzdWIiOiJ1dWlkLTEyMyIsImVtYWlsIjoiYWRtaW5AY2FwZmxvdy5jb20ifQ.assinatura"
        fake_payload = {
            "sub": "uuid-supabase-123",
            "email": "admin@capflow.com",
            "aud": "authenticated",
            "user_metadata": {
                "nome": "Felipe Admin",
                "cargo": "GERENTE",
                "empresa": "Bonelaria Alpha",
            },
        }

        jwt_client = APIClient()
        with patch("estoque.supabase_auth.decode_supabase_jwt", return_value=fake_payload):
            res_me = jwt_client.get(
                "/api/me/",
                HTTP_AUTHORIZATION=f"Token {fake_jwt}",
            )
            self.assertEqual(res_me.status_code, status.HTTP_200_OK)
            self.assertEqual(res_me.data["username"], "admin@capflow.com")
            self.assertEqual(res_me.data["cargo"], "GERENTE")

