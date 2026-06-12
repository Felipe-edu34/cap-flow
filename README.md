# 🧢 CapFlow - Sistema de Gestão de Estoque Setorizado

An API built with Django and Django REST Framework designed to solve a real production problem in a cap factory (bonelaria). It replaces informal tools (like Microsoft To Do) with a structured, secure, and role-based inventory control system.

---

## 📌 O Problema Real & A Solução

**O Cenário:** A fábrica gerenciava o fluxo de matérias-primas e produtos acabados de forma improvisada, gerando falta de rastreabilidade e furos no estoque.  
**A Solução:** O **CapFlow** centraliza o controle. O administrador (proprietário/secretários) gerencia permissões via painel web, determinando exatamente qual setor (ex: Costura, Abas, Embalagem) cada funcionário pode acessar. Os operadores interagem com o estoque de forma simplificada por meio de uma interface mobile integrada à API.

---

## 🚀 Funcionalidades Principais

- **🔒 Controle de Acesso Baseado em Funções (RBAC):** Funcionários comuns visualizam e alteram *apenas* os itens dos setores aos quais o administrador os vinculou.
- **📈 Histórico de Movimentação Automatizado (Logs):** Cada entrada ou saída registra silenciosamente o usuário, data, hora, quantidade e observações, garantindo auditoria completa para o dono do negócio.
- **🚨 Alerta de Estoque Mínimo:** Monitoramento preventivo de insumos para evitar a paralisação da linha de produção.
- **🖥️ Painel Administrativo Pronto:** Utilização do ecossistema nativo do Django customizado com filtros avançados e buscas otimizadas.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.x
- **Framework Principal:** Django 5.x / 6.x
- **API Engine:** Django REST Framework (DRF)
- **Banco de Dados:** SQLite (Ambiente de desenvolvimento) / Suporte nativo para PostgreSQL
- **Autenticação:** Token/Session Based Authentication (Padrão DRF)

---

## 📐 Estrutura do Banco de Dados (Models)

O coração do sistema baseia-se em três entidades principais fortemente relacionadas:

1. **Setor:** Define os departamentos da fábrica e mapeia o relacionamento *Many-to-Many* com os usuários permitidos.
2. **ItemEstoque:** Contém os insumos/produtos, quantidade atual, unidade de medida e limites mínimos, vinculados a um *Setor*.
3. **Movimentacao:** Tabela imutável de log que registra o histórico detalhado de `ENTRADA` e `SAIDA`.

---

## 🔧 Como Executar o Projeto Localmente

### Pré-requisitos
- Python instalado (versão 3.10 ou superior)
- Git instalado

### Passo a Passo

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/SEU_USUARIO/cap-flow.git](https://github.com/SEU_USUARIO/cap-flow.git)
   cd cap-flow
