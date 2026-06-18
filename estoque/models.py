from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver

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
# Procure pelo seu modelo ItemEstoque e deixe-o assim:
class ItemEstoque(models.Model):
    nome = models.CharField(max_length=100)
    quantidade_atual = models.IntegerField(default=0)
    unidade_medida = models.CharField(max_length=10, default='UN')
    estoque_minimo = models.IntegerField(default=0)
    setor = models.ForeignKey('Setor', on_delete=models.CASCADE)
    
    # ADICIONE ESTE CAMPO para receber o gerenteId do formulário do frontend
    gerente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True) 

    def __str__(self):
        return self.nome

# 5. O HISTÓRICO DE MOVIMENTAÇÕES
# 5. O HISTÓRICO DE MOVIMENTAÇÕES (Unificado e Corrigido)
class Movimentacao(models.Model):
    TIPOS_MOV = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    )
    # Correção: Aponta para o modelo correto (ItemEstoque)
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=10, choices=TIPOS_MOV)
    quantidade_movimentada = models.IntegerField(default=0)
    data_movimentacao = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-data_movimentacao'] # Exibe as movimentações mais recentes primeiro

    def __str__(self):
        return f"{self.tipo} - {self.item.nome} ({self.quantidade_movimentada})"
    
@receiver(pre_save, sender=ItemEstoque)
def rastrear_movimentacao_estoque(sender, instance, **kwargs):
    # Se o produto já existia no banco de dados, checamos a diferença
    if instance.pk:
        anterior = ItemEstoque.objects.get(pk=instance.pk)
        diferenca = instance.quantidade_atual - anterior.quantidade_atual
        
        if diferenca > 0:
            Movimentacao.objects.create(
                item=instance,
                tipo='ENTRADA',
                quantidade_movimentada=diferenca,
                observacao="Quantidade atualizada via painel administrativo."
            )
        elif diferenca < 0:
            Movimentacao.objects.create(
                item=instance,
                tipo='SAIDA',
                quantidade_movimentada=abs(diferenca),
                observacao="Retirada/Ajuste de estoque via painel administrativo."
            )
    else:
        # Se for um produto novo sendo cadastrado do zero
        # Só criamos se ele começar com uma quantidade maior que zero
        if instance.quantidade_atual > 0:
            # Usamos um truque de pós-salvamento manual porque o objeto precisa de ID primeiro
            pass