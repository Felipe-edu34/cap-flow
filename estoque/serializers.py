from rest_framework import serializers
from .models import Setor, ItemEstoque, Movimentacao

class ItemEstoqueSerializer(serializers.ModelSerializer):
    # Mostraremos o nome do setor em formato de texto na API
    setor_nome = serializers.CharField(source='setor.nome', read_only=True)

    class Meta:
        model = ItemEstoque
        fields = ['id', 'nome', 'quantidade_atual', 'unidade_medida', 'estoque_minimo', 'setor', 'setor_nome']

class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        fields = ['id', 'item', 'usuario', 'tipo', 'quantidade_movimentada', 'data_hora', 'observacao']