from django.contrib import admin
from .models import Setor, ItemEstoque, Movimentacao

# O @admin.register "conecta" a nossa tabela com o painel visual
@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    # list_display diz quais colunas vão aparecer na tela inicial do painel
    list_display = ('nome',)

@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ('nome', 'setor', 'quantidade_atual', 'unidade_medida')
    # list_filter cria um menu lateral direito para o patrão filtrar os itens por setor
    list_filter = ('setor',)
    # search_fields cria uma barra de pesquisa no topo
    search_fields = ('nome',)

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'quantidade_movimentada', 'usuario', 'data_hora')
    list_filter = ('tipo', 'usuario', 'data_hora')