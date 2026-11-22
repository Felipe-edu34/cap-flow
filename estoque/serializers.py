from rest_framework import serializers
from .models import Setor, SubSetor, ItemEstoque, Movimentacao, Funcionario


class SetorSerializer(serializers.ModelSerializer):
    empresa_nome = serializers.CharField(source='empresa.nome_fantasia', read_only=True)
    # 1. Trocamos o CharField por um SerializerMethodField para lidar com a lista
    responsaveis_nomes = serializers.SerializerMethodField()

    class Meta:
        model = Setor
        # 2. Atualizamos os nomes dos campos para bater com o banco de dados
        fields = ['id', 'nome', 'empresa', 'empresa_nome', 'responsaveis', 'responsaveis_nomes']
        read_only_fields = ['empresa']

    # 3. Essa função pega todas as pessoas ligadas ao setor e cria uma lista de nomes
    def get_responsaveis_nomes(self, obj):
        return [user.username for user in obj.responsaveis.all()]


# NOVO SERIALIZADOR
class SubSetorSerializer(serializers.ModelSerializer):
    setor_pai_nome = serializers.CharField(source='setor_pai.nome', read_only=True)

    class Meta:
        model = SubSetor
        fields = ['id', 'nome', 'setor_pai', 'setor_pai_nome']


class ItemEstoqueSerializer(serializers.ModelSerializer):
    # Agora pegamos o nome do subsetor e também rastreamos o nome do setor pai!
    subsetor_nome = serializers.CharField(source='subsetor.nome', read_only=True)
    setor_nome = serializers.CharField(source='subsetor.setor_pai.nome', read_only=True)
    gerente_nome = serializers.CharField(source='gerente.username', read_only=True)

    class Meta:
        model = ItemEstoque
        # Atualizamos os campos para incluir o subsetor
        fields = [
            'id', 'nome', 'quantidade_atual', 'unidade_medida',
            'estoque_minimo', 'subsetor', 'subsetor_nome', 'setor_nome', 'gerente', 'gerente_nome', 'imagem'
        ]

    def validate_quantidade_atual(self, value):
        if value < 0:
            raise serializers.ValidationError("A quantidade em estoque não pode ser negativa.")
        return value

    def validate_estoque_minimo(self, value):
        if value < 0:
            raise serializers.ValidationError("O estoque mínimo não pode ser negativo.")
        return value


class MovimentacaoSerializer(serializers.ModelSerializer):
    quantidade = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Movimentacao
        fields = ['id', 'item', 'tipo', 'quantidade_movimentada', 'quantidade', 'data_movimentacao', 'observacao']

    def validate(self, attrs):
        # Compatibilidade com o frontend mobile que envia 'quantidade' ou 'quantidade_movimentada'
        quantidade_alias = attrs.pop('quantidade', None)
        if 'quantidade_movimentada' not in attrs and quantidade_alias is not None:
            attrs['quantidade_movimentada'] = quantidade_alias

        qtd = attrs.get('quantidade_movimentada')
        if qtd is None or qtd <= 0:
            raise serializers.ValidationError({
                "quantidade_movimentada": "A quantidade movimentada deve ser maior que zero."
            })

        return attrs


class FuncionarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Funcionario
        fields = '__all__'