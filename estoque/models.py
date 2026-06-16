from django.db import models
from django.contrib.auth.models import User

# 1. A TABELA MÃE: EMPRESA
class Empresa(models.Model):
    nome_fantasia = models.CharField(max_length=150)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_fantasia

# 2. O CRACHÁ DO USUÁRIO: PERFIL
# Estende o usuário padrão do Django para adicionar o Cargo e a Empresa
class Perfil(models.Model):
    TIPOS_CARGO = (
        ('GERENTE', 'Gerente'),
        ('FUNCIONARIO', 'Funcionário'),
    )
    
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=20, choices=TIPOS_CARGO, default='FUNCIONARIO')

    def __str__(self):
        return f"{self.usuario.username} | {self.cargo} ({self.empresa.nome_fantasia})"

# 3. O SETOR (Agora pertence a uma Empresa)
class Setor(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome_fantasia}"

# 4. O ITEM DE ESTOQUE (Pertence ao Setor, que pertence à Empresa)
class ItemEstoque(models.Model):
    # ... (seus campos antigos: nome, quantidade_atual, etc) ...
    nome = models.CharField(max_length=100)
    quantidade_atual = models.IntegerField(default=0)
    unidade_medida = models.CharField(max_length=10, default='UN')
    estoque_minimo = models.IntegerField(default=0)
    setor = models.ForeignKey('Setor', on_delete=models.CASCADE)
    
    # NOVO CAMPO: null=True e blank=True significam que a foto é opcional
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True) 

    def __str__(self):
        return self.nome

# 5. O HISTÓRICO DE MOVIMENTAÇÕES
class Movimentacao(models.Model):
    TIPOS_MOV = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    )
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=10, choices=TIPOS_MOV)
    quantidade_movimentada = models.DecimalField(max_digits=10, decimal_places=2)
    data_movimentacao = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} - {self.item.nome} ({self.quantidade_movimentada})"