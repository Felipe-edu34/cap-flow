from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver

class Empresa(models.Model):
    nome_fantasia = models.CharField(max_length=150)
    cnpj = models.CharField(max_length=20, blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_fantasia

class Perfil(models.Model):
    # Atualize para bater com as opções do React Native!
    TIPOS_CARGO = (
        ('ADMINISTRADOR', 'Administrador'),
        ('GESTOR', 'Gestor'),
        ('OPERADOR', 'Operador'),
        ('GERENTE', 'Gerente'), # mantido caso use em outra parte
    )
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cargo = models.CharField(max_length=20, choices=TIPOS_CARGO, default='OPERADOR') # padrão operador

    def __str__(self):
        return f"{self.usuario.username} | {self.cargo} ({self.empresa.nome_fantasia})"
    
class Setor(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=100)
    
    # 🔥 A MÁGICA ACONTECE AQUI:
    # Trocamos de 'responsavel' (ForeignKey) para 'responsaveis' (ManyToManyField)
    responsaveis = models.ManyToManyField(User, blank=True, related_name='setores_gerenciados')

    def __str__(self):
        return f"{self.nome} - {self.empresa.nome_fantasia}"

class SubSetor(models.Model):
    setor_pai = models.ForeignKey(Setor, on_delete=models.CASCADE, related_name='subsetores')
    nome = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nome} (pertence a: {self.setor_pai.nome})"

class ItemEstoque(models.Model):
    nome = models.CharField(max_length=100)
    quantidade_atual = models.IntegerField(default=0)
    unidade_medida = models.CharField(max_length=10, default='UN')
    estoque_minimo = models.IntegerField(default=0)
    subsetor = models.ForeignKey(SubSetor, on_delete=models.CASCADE, related_name='produtos')
    gerente = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    imagem = models.ImageField(upload_to='produtos/', null=True, blank=True) 

    def __str__(self):
        return self.nome

class Movimentacao(models.Model):
    TIPOS_MOV = (
        ('ENTRADA', 'Entrada'),
        ('SAIDA', 'Saída'),
    )
    item = models.ForeignKey(ItemEstoque, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=10, choices=TIPOS_MOV)
    quantidade_movimentada = models.IntegerField(default=0)
    data_movimentacao = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-data_movimentacao']

    def __str__(self):
        return f"{self.tipo} - {self.item.nome} ({self.quantidade_movimentada})"

@receiver(pre_save, sender=ItemEstoque)
def rastrear_movimentacao_estoque(sender, instance, **kwargs):
    if instance.pk:
        anterior = ItemEstoque.objects.get(pk=instance.pk)
        diferenca = instance.quantidade_atual - anterior.quantidade_atual
        if diferenca > 0:
            Movimentacao.objects.create(item=instance, tipo='ENTRADA', quantidade_movimentada=diferenca, observacao="Quantidade atualizada.")
        elif diferenca < 0:
            Movimentacao.objects.create(item=instance, tipo='SAIDA', quantidade_movimentada=abs(diferenca), observacao="Retirada/Ajuste.")



class Funcionario(models.Model):
    CARGOS_CHOICES = [
        ('ADMINISTRADOR', 'Administrador'),
        ('GESTOR', 'Gestor'),
        ('OPERADOR', 'Operador'),
    ]
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('INATIVO', 'Inativo'),
    ]

    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    senha = models.CharField(max_length=255)  # No futuro vamos usar make_password aqui para segurança!
    cargo = models.CharField(max_length=50, choices=CARGOS_CHOICES, default='OPERADOR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ATIVO')
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome