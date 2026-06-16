from rest_framework import serializers
from .models import Setor, ItemEstoque, Movimentacao

class ItemEstoqueSerializer(serializers.ModelSerializer):
    setor_nome = serializers.CharField(source='setor.nome', read_only=True)

    class Meta:
        model = ItemEstoque
        fields = ['id', 'nome', 'quantidade_atual', 'unidade_medida', 'estoque_minimo', 'setor', 'setor_nome']

class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        # Atualizamos data_hora para data_movimentacao e removemos o usuario (que não está mais nessa tabela)
        fields = ['id', 'item', 'tipo', 'quantidade_movimentada', 'data_movimentacao', 'observacao']