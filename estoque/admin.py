from django.contrib import admin
from .models import Empresa, Perfil, Setor, SubSetor, ItemEstoque, Movimentacao

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'cnpj', 'criado_em')
    search_fields = ('nome_fantasia', 'cnpj')

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'cargo', 'empresa')
    list_filter = ('cargo', 'empresa')
    search_fields = ('usuario__username',)

@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    # 1. Tire o 'responsavel' daqui e coloque a função que vamos criar abaixo:
    list_display = ('id', 'nome', 'empresa', 'get_responsaveis') 
    
    # (Mantenha os outros campos como search_fields, se tiver)

    # 2. Adicione esta função para mostrar a listinha de nomes na tela do Admin:
    def get_responsaveis(self, obj):
        # Pega todos os responsáveis e junta os nomes com vírgula
        return ", ".join([user.username for user in obj.responsaveis.all()])
    
    # Dá um título bonito para a coluna no painel Admin
    get_responsaveis.short_description = 'Responsáveis'

# --- NOVO: Adicionamos o painel do Sub-setor ---
@admin.register(SubSetor)
class SubSetorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'setor_pai')
    list_filter = ('setor_pai__empresa', 'setor_pai')
    search_fields = ('nome',)

@admin.register(ItemEstoque)
class ItemEstoqueAdmin(admin.ModelAdmin):
    # ATENÇÃO: Mudamos de 'setor' para 'subsetor'
    list_display = ('nome', 'subsetor', 'quantidade_atual', 'unidade_medida', 'estoque_minimo')
    list_filter = ('subsetor__setor_pai__empresa', 'subsetor__setor_pai', 'subsetor') 
    search_fields = ('nome',)

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display = ('item', 'tipo', 'quantidade_movimentada', 'data_movimentacao')
    # ATENÇÃO: O caminho do filtro agora passa pelo subsetor e setor pai
    list_filter = ('tipo', 'data_movimentacao', 'item__subsetor__setor_pai__empresa') 
    search_fields = ('item__nome',)