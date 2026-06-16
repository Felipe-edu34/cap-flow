from rest_framework import serializers
from .models import Setor, ItemEstoque, Movimentacao


class SetorSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.CharField(source='empresa.nome_fantasia', read_only=True)
    responsavel_nome = serializers.CharField(source='responsavel.username', read_only=True)

    class Meta:
        model = Setor
        fields = ['id', 'nome', 'empresa', 'empresa_nome', 'responsavel', 'responsavel_nome']
        read_only_fields = ['empresa']


class ItemEstoqueSerializer(serializers.ModelSerializer):
    setor_nome = serializers.CharField(source='setor.nome', read_only=True)
    # Traz o nome do gerente mapeado também para a ficha técnica do modal se precisar
    gerente_nome = serializers.CharField(source='gerente.username', read_only=True)

    class Meta:
        model = ItemEstoque
        # Adicione 'gerente' e 'gerente_nome' na lista de campos
        fields = [
            'id', 'nome', 'quantidade_atual', 'unidade_medida', 
            'estoque_minimo', 'setor', 'setor_nome', 'gerente', 'gerente_nome', 'imagem'
        ]

class MovimentacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movimentacao
        # Atualizamos data_hora para data_movimentacao e removemos o usuario (que não está mais nessa tabela)
        fields = ['id', 'item', 'tipo', 'quantidade_movimentada', 'data_movimentacao', 'observacao']
