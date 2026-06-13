from django.db import models
from django.contrib.auth.models import User

# --- NOVA TABELA PARA MULTI-EMPRESAS ---
class Empresa(models.Model):
    nome_fantasia = models.CharField(max_length=150)
    cnpj = models.CharField(max_length=18, unique=True, blank=True, null=True)
    dono = models.OneToOneField(User, on_delete=models.CASCADE, related_name='empresa_administrada')

    def __str__(self):
        return self.nome_fantasia


class Setor(models.Model):
    # EVOLUÇÃO: Cada empresa cria e enxerga apenas os seus próprios setores!
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='setores', null=True, blank=True)
    nome = models.CharField(max_length=100, help_text="Ex: Tecidos, Fios, Abas")
    responsaveis = models.ManyToManyField(User, related_name='setores_permitidos', blank=True)

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome_fantasia if self.empresa else 'Geral'}"


class ItemEstoque(models.Model):
    UNIDADES_CHOICES = [
        ('UN', 'Unidade'),
        ('MT', 'Metros'),
        ('RL', 'Rolo'),
        ('KG', 'Quilos'),
        ('CX', 'Caixa'),
    ]

    nome = models.CharField(max_length=150, help_text="Ex: Rolo de tecido preto")
    setor = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='itens')
    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unidade_medida = models.CharField(max_length=2, choices=UNIDADES_CHOICES, default='UN')
    estoque_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Alerta o patrão se baixar desse valor")

    def __str__(self):
        return f"{self.nome} ({self.quantidade_atual} {self.unidade_medida})"


class Movimentacao(models.Model):
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada (+)'),
        ('SAIDA', 'Saída (-)'),
    ]

    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE, related_name='historico_movimentacoes')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, help_text="Quem fez a alteração no app")
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    quantidade_movimentada = models.DecimalField(max_digits=10, decimal_places=2)
    data_hora = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField(blank=True, null=True, help_text="Ex: Tecido veio com defeito")

    def __str__(self):
        return f"{self.tipo} de {self.quantidade_movimentada} em {item.nome}"