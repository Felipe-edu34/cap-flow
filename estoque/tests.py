from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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

    def test_signal_rastrear_movimentacao_estoque_branches(self):
        # 1. Criação inicial (instance.pk is None no pre_save) -> não deve disparar signal de update
        item = ItemEstoque.objects.create(
            nome="Botão Pressão",
            quantidade_atual=10,
            subsetor=self.subsetor,
        )
        self.assertEqual(Movimentacao.objects.filter(item=item).count(), 0)

        # 2. Incremento unitário (+1) -> testa fronteira diferenca > 0 vs diferenca > 1
        item.quantidade_atual = 11
        item.save()
        movs = Movimentacao.objects.filter(item=item)
        self.assertEqual(movs.count(), 1)
        mov_entrada = movs.first()
        self.assertEqual(mov_entrada.tipo, "ENTRADA")
        self.assertEqual(mov_entrada.quantidade_movimentada, 1)
        self.assertEqual(mov_entrada.observacao, "Quantidade atualizada.")

        # 3. Salvar sem alterar quantidade (diferenca == 0) -> não deve criar movimentação
        item.nome = "Botão Pressão Inox"
        item.save()
        self.assertEqual(Movimentacao.objects.filter(item=item).count(), 1)

        # 4. Decremento unitário (-1) e maior (-3) -> testa fronteira diferenca < 0 e abs(diferenca)
        item.quantidade_atual = 10
        item.save()
        self.assertEqual(Movimentacao.objects.filter(item=item).count(), 2)
        mov_saida_1 = Movimentacao.objects.filter(item=item, tipo="SAIDA").first()
        self.assertIsNotNone(mov_saida_1)
        self.assertEqual(mov_saida_1.quantidade_movimentada, 1)
        self.assertEqual(mov_saida_1.observacao, "Retirada/Ajuste.")

        item.quantidade_atual = 7
        item.save()
        mov_saida_3 = Movimentacao.objects.filter(item=item, tipo="SAIDA", quantidade_movimentada=3).first()
        self.assertIsNotNone(mov_saida_3)
        self.assertEqual(mov_saida_3.observacao, "Retirada/Ajuste.")

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
