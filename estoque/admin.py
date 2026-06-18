from django.contrib import admin
from .models import Empresa, Perfil, Setor, ItemEstoque, Movimentacao

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    # Mostra essas colunas na tabela principal do Admin
    list_display = ('nome_fantasia', 'cnpj', 'criado_em')
    search_fields = ('nome_fantasia', 'cnpj')

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cargo', 'empresa')
    list_filter = ('cargo', 'empresa')
    search_fields = ('usuario__username',)

@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'responsavel')
    list_filter = ('empresa',)
    search_fields = ('nome',)

@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ('nome', 'setor', 'quantidade_atual', 'unidade_medida', 'estoque_minimo')
    list_filter = ('setor__empresa', 'setor') # Filtro duplo lindão
    search_fields = ('nome',)

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'quantidade_movimentada', 'data_movimentacao')
    list_filter = ('tipo', 'data_movimentacao', 'item__setor__empresa') # Agora funciona perfeitamente!
    search_fields = ('item__nome',)