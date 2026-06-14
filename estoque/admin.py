from django.contrib import admin
from .models import Empresa, Setor, ItemEstoque, Movimentacao

# --- REGISTRO DA NOVA TABELA DE EMPRESAS ---
@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    # Mostra o nome da empresa, CNPJ e quem é o usuário dono/administrador dela
    list_display = ('nome_fantasia', 'cnpj', 'dono')
    search_fields = ('nome_fantasia', 'cnpj')


# --- ATUALIZAÇÃO DO SETOR (AMARRADO À EMPRESA) ---
@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    # Agora exibe o nome do setor e qual empresa é a dona dele
    list_display = ('nome', 'empresa')
    # Cria um filtro lateral para você ver os setores de uma empresa específica
    list_filter = ('empresa',)
    search_fields = ('nome',)


@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    list_display = ('nome', 'setor', 'quantidade_atual', 'unidade_medida')
    list_filter = ('setor',)
    search_fields = ('nome',)


@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'quantidade_movimentada', 'usuario', 'data_hora')
    list_filter = ('tipo', 'usuario', 'data_hora')