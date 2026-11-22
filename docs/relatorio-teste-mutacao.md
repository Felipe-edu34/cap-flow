# Relatório Técnico — Projeto 03: Teste de Mutação e Ampliação da Cobertura

## 1. Identificação e Stack

- **Grupo:** G6 — CapFlow (Sistema de Gestão de Estoque Setorizado)
- **Integrante Responsável:** Felipe Eduardo Silva Fernandes (`@Felipe-edu34`)
- **Repositório:** Backend API (`cap-flow`)
- **Branch de Trabalho:** `test/#1-teste-mutacao`
- **Stack Tecnológica:** Python 3.14 / Django 6.1 / Django REST Framework 3.18
- **Ferramenta de Teste de Mutação:** `mutmut` (v2.5.1) integrada ao Django Test Runner (`manage.py test`) e `pytest-django`
- **Módulo Alvo da Mutação:** `estoque/models.py` (Entidades principais de domínio e sinal `pre_save` de auditoria automática de movimentações de estoque)

---

## 2. Fundamentação Teórica Breve

O **Teste de Mutação** é uma técnica de teste baseada em defeitos (*fault-based testing*) que avalia a qualidade e a eficácia real de uma suíte de testes unitários. Enquanto a cobertura de código tradicional (*line/branch coverage*) mede apenas se uma linha foi **executada** durante os testes, o teste de mutação verifica se os testes possuem **asserções fortes o suficiente para detectar falhas** caso a lógica daquela linha seja corrompida.

Durante o processo, a ferramenta `mutmut` analisa a Árvore Sintática Abstrata (AST) do código-fonte e aplica **Operadores de Mutação** (pequenos desvios sintáticos que simulam erros reais de programação), gerando versões modificadas do sistema chamadas **Mutantes**:

1. **Operadores Relacionais (ROR):** Substituição de `>` por `>=`, `<` por `<=`, `==` por `!=`, ou deslocamento de fronteiras numéricas (ex.: `diferenca > 0` $\rightarrow$ `diferenca > 1`).
2. **Operadores Aritméticos (AOR):** Troca de operadores matemáticos (ex.: `instance.quantidade_atual - anterior.quantidade_atual` $\rightarrow$ `instance.quantidade_atual + anterior.quantidade_atual`).
3. **Mutação de Constantes e Literais (CRP):** Alteração de literais numéricos (`0` $\rightarrow$ `1`, `150` $\rightarrow$ `151`) e corrupção de strings de domínio (`'ENTRADA'` $\rightarrow$ `'XXENTRADAXX'`, `'SAIDA'` $\rightarrow$ `'XXSAIDAXX'`).
4. **Operadores Booleanos e de Atribuição:** Inversão de valores lógicos (`True` $\rightarrow$ `False`, como em `unique=True` ou `blank=True`) e anulação de declarações (`campo = None`).

Para cada mutante gerado, a suíte de testes é executada:
- Se ao menos um teste falhar, o mutante é considerado **Morto (*Killed* — 🎉)**, provando que a suíte detectou o defeito injetado.
- Se todos os testes continuarem passando, o mutante é considerado **Sobrevivente (*Survived* — 🙁)**, evidenciando ausência de testes para aquele cenário, fraqueza nas asserções ou a presença de um **Mutante Equivalente**.

A eficácia da suíte é quantificada pelo **Mutant Score**:

$$\text{Mutant Score} = \left( \frac{\text{Mutantes Mortos}}{\text{Total de Mutantes Válidos}} \right) \times 100\%$$

---

## 3. Instruções de Execução

### 3.1. Instalação das Dependências
Com o ambiente virtual (`venv`) ativado na raiz do projeto:
```bash
./venv/bin/pip install "mutmut<3" pytest pytest-django
```

### 3.2. Configuração (`setup.cfg`)
O arquivo `setup.cfg` na raiz do repositório define o módulo de regras de negócio alvo da mutação e o comando de execução da suíte de testes:
```ini
[mutmut]
paths_to_mutate=estoque/models.py
runner=./venv/bin/python manage.py test estoque
tests_dir=estoque/
```

### 3.3. Comandos Principais de Execução
- **Executar a suíte de testes unitários do Django:**
  ```bash
  ./venv/bin/python manage.py test estoque
  ```
- **Executar o ciclo completo de teste de mutação:**
  ```bash
  ./venv/bin/mutmut run
  ```
- **Visualizar o resumo dos resultados e IDs sobreviventes:**
  ```bash
  ./venv/bin/mutmut results
  ```
- **Inspecionar o `diff` exato de um mutante específico:**
  ```bash
  ./venv/bin/mutmut show <id>
  ```

---

## 4. Tabela Comparativa de Métricas (Antes × Depois)

Na medição inicial (**ANTES**), a suíte contava apenas com 2 testes superficiais de criação e `__str__`. Após a análise dos 89 mutantes sobreviventes, a suíte em `estoque/tests.py` foi ampliada (**DEPOIS**) para 7 métodos de teste abrangentes cobrindo todos os fluxos do signal `rastrear_movimentacao_estoque`, valores limite, escolhas de domínio (`choices`), valores padrão (`default`) e restrições de metadados dos modelos.

| Métrica Avaliada | Medição Inicial (ANTES) | Medição Final (DEPOIS) | Evolução / Impacto |
| :--- | :---: | :---: | :---: |
| **Testes Unitários na Suíte (`estoque/tests.py`)** | 2 | 7 | +5 conjuntos de testes completos |
| **Total de Mutantes Gerados** | 112 | 112 | Mesma base de código (`estoque/models.py`) |
| **Mutantes Mortos (*Killed* — 🎉)** | 23 | **112** | **+89 mutantes eliminados** |
| **Mutantes Sobreviventes (*Survived* — 🙁)** | 89 | **0** | **-100% de sobreviventes** |
| **Mutantes com Timeout (*Timeout* — ⏰)** | 0 | 0 | 0 |
| **Mutantes com Erro / Suspeitos (🤔 / 🔇)** | 0 | 0 | 0 |
| **Mutant Score (`Mortos / Total * 100%`)** | **20,54%** | **100,00%** | **+79,46 pontos percentuais (Meta $\ge 70\%$ atingida)** |

---

## 5. Estudo de Caso de Mutantes

Abaixo são detalhados 3 mutantes críticos que sobreviveram na primeira execução e como foram sistematicamente eliminados, além da discussão técnica sobre mutantes equivalentes em modelos ORM.

### 5.1. Caso 1 — Mutante #80 (Alteração de Condição de Fronteira em Regra de Negócio)
**Diff do Mutante (`mutmut show 80`):**
```diff
--- estoque/models.py
+++ estoque/models.py
@@ -78,7 +78,7 @@
     if instance.pk:
         anterior = ItemEstoque.objects.get(pk=instance.pk)
         diferenca = instance.quantidade_atual - anterior.quantidade_atual
-        if diferenca > 0:
+        if diferenca > 1:
             Movimentacao.objects.create(item=instance, tipo='ENTRADA', quantidade_movimentada=diferenca, observacao="Quantidade atualizada.")
         elif diferenca < 0:
             Movimentacao.objects.create(item=instance, tipo='SAIDA', quantidade_movimentada=abs(diferenca), observacao="Retirada/Ajuste.")
```
- **Por que sobreviveu inicialmente:** O sinal `pre_save` (`rastrear_movimentacao_estoque`) monitora atualizações em `ItemEstoque` e gera automaticamente um registro de auditoria em `Movimentacao`. O mutante alterou a fronteira `diferenca > 0` para `diferenca > 1`, fazendo com que qualquer entrada unitária (`+1` unidade no estoque) fosse silenciosamente ignorada sem gerar log. Como a suíte inicial não testava atualizações com incremento de valor limite (`+1`), o mutante sobreviveu.
- **Como foi morto em `estoque/tests.py`:** Adicionamos no método `test_signal_rastrear_movimentacao_estoque_branches` um teste de valor limite que incrementa `item.quantidade_atual` de `10` para `11` (`diferenca == 1`), salva o objeto e verifica:
  ```python
  item.quantidade_atual = 11
  item.save()
  mov_entrada = Movimentacao.objects.filter(item=item).first()
  self.assertEqual(mov_entrada.tipo, "ENTRADA")
  self.assertEqual(mov_entrada.quantidade_movimentada, 1)
  self.assertEqual(mov_entrada.observacao, "Quantidade atualizada.")
  ```

---

### 5.2. Caso 2 — Mutante #77 (Inversão de Operador Aritmético no Cálculo de Saldo)
**Diff do Mutante (`mutmut show 77`):**
```diff
--- estoque/models.py
+++ estoque/models.py
@@ -77,7 +77,7 @@
 def rastrear_movimentacao_estoque(sender, instance, **kwargs):
     if instance.pk:
         anterior = ItemEstoque.objects.get(pk=instance.pk)
-        diferenca = instance.quantidade_atual - anterior.quantidade_atual
+        diferenca = instance.quantidade_atual + anterior.quantidade_atual
         if diferenca > 0:
             Movimentacao.objects.create(item=instance, tipo='ENTRADA', quantidade_movimentada=diferenca, observacao="Quantidade atualizada.")
         elif diferenca < 0:
```
- **Por que sobreviveu inicialmente:** O operador de subtração (`-`) foi substituído por adição (`+`). Com essa mutação, ao atualizar um estoque de `10` para `11`, a diferença calculada passava a ser `21` em vez de `1`, e qualquer redução de estoque (ex.: de `10` para `7`) resultava em `+17` (registrando uma falsa `ENTRADA` em vez de `SAIDA`). Sobreviveu porque o sinal `pre_save` não possuía asserções sobre o valor exato de `quantidade_movimentada`.
- **Como foi morto em `estoque/tests.py`:** Ao asserir que o incremento de `10` para `11` gera `quantidade_movimentada == 1` e que a redução de `10` para `7` gera um registro do tipo `'SAIDA'` com `quantidade_movimentada == 3`, qualquer alteração no operador aritmético quebra imediatamente o teste.

---

### 5.3. Caso 3 — Mutantes #83 e #85 (Corrupção do Ramo de Saída e Literal de Domínio)
**Diff dos Mutantes (`mutmut show 83` e `mutmut show 85`):**
```diff
--- estoque/models.py
+++ estoque/models.py
@@ -80,8 +80,8 @@
         diferenca = instance.quantidade_atual - anterior.quantidade_atual
         if diferenca > 0:
             Movimentacao.objects.create(item=instance, tipo='ENTRADA', quantidade_movimentada=diferenca, observacao="Quantidade atualizada.")
-        elif diferenca < 0:
-            Movimentacao.objects.create(item=instance, tipo='SAIDA', quantidade_movimentada=abs(diferenca), observacao="Retirada/Ajuste.")
+        elif diferenca <= 0:
+            Movimentacao.objects.create(item=instance, tipo='XXSAIDAXX', quantidade_movimentada=abs(diferenca), observacao="Retirada/Ajuste.")
```
- **Por que sobreviveram inicialmente:**
  - No **Mutante #83**, a condição `diferenca < 0` virou `diferenca <= 0`. Isso causava um bug crítico: salvar um produto editando apenas o seu `nome` (onde `diferenca == 0`) disparava a criação indevida de uma movimentação de `SAIDA` com quantidade `0`.
  - No **Mutante #85**, o tipo `'SAIDA'` foi corrompido para `'XXSAIDAXX'`.
- **Como foram mortos em `estoque/tests.py`:**
  1. Para matar o **Mutante #83**, criamos um passo específico onde alteramos apenas `item.nome = "Botão Pressão Inox"` mantendo a mesma quantidade (`diferenca == 0`) e asserimos que a contagem de movimentações no banco permanece inalterada (`count() == 1`).
  2. Para matar o **Mutante #85**, reduzimos a quantidade do item e asserimos explicitamente `tipo="SAIDA"`, `quantidade_movimentada=3` e `observacao="Retirada/Ajuste."`.

---

### 5.4. Análise de Mutantes Equivalentes / Semântica ORM (Mutante #1)
**Diff do Mutante (`mutmut show 1`):**
```diff
--- estoque/models.py
+++ estoque/models.py
@@ -4,7 +4,7 @@
 from django.dispatch import receiver
 
 class Empresa(models.Model):
-    nome_fantasia = models.CharField(max_length=150)
+    nome_fantasia = models.CharField(max_length=151)
     cnpj = models.CharField(max_length=20, blank=True, null=True)
     criado_em = models.DateTimeField(auto_now_add=True)
```
- **Justificativa Técnica (Comportamento Equivalente no SQLite vs. Introspecção de Metadados):**
  Em aplicações Django que utilizam SQLite em ambiente de testes, uma chamada `Empresa.objects.create(nome_fantasia="...")` executa um `INSERT` direto sem invocar `full_clean()`, e o motor SQLite não impõe truncamento ou erro em `VARCHAR(150)` vs `VARCHAR(151)`. Portanto, sob a ótica puramente funcional de banco de dados em memória para entradas válidas do domínio, o Mutante #1 atua como um **Mutante Comportamentalmente Equivalente** (a alteração sintática de `150` para `151` não altera nenhuma saída funcional das operações CRUD).
- **Estratégia Adotada:** Para evitar que mutações em contratos de schema do Django (`max_length`, `blank`, `null`, `unique`, `related_name`, `upload_to` e `auto_now_add`) mascarassem falhas reais ou inflassem a lista de sobreviventes, adicionamos testes de contrato de metadados via API `_meta.get_field()` do Django. Dessa forma, garantimos a integridade estrutural do schema e eliminamos 100% dos mutantes gerados.

---

## 6. Conclusões da Equipe

A aplicação prática do Teste de Mutação com o `mutmut` no backend do **CapFlow** demonstrou na prática a diferença entre *executar código* e *testar código*:

1. **Descoberta de Pontos Cegos em Regras Críticas:** Mesmo com testes básicos que instanciavam os modelos sem erros, o **Mutant Score inicial de 20,54%** revelou que a regra de negócio mais sensível do domínio — o rastreamento automático de entradas e saídas de estoque via sinal `pre_save` (`rastrear_movimentacao_estoque`) — estava completamente desprotegida contra regressões.
2. **Importância dos Testes de Valor Limite (*Boundary Value Analysis*):** Mutantes como o `#80` (`diferenca > 0` $\rightarrow$ `diferenca > 1`) e o `#83` (`diferenca < 0` $\rightarrow$ `diferenca <= 0`) provaram que testar apenas um caso genérico não basta; foi indispensável testar explicitamente as fronteiras `diferenca == +1`, `diferenca == 0` (atualização cadastral sem mudança de saldo) e `diferenca == -1`, além da criação inicial (`instance.pk is None`).
3. **Confiabilidade e Prevenção de Regressões:** Ao evoluir o Mutant Score de **20,54% para 100,00%** (112 de 112 mutantes mortos), a equipe passa a contar com uma rede de segurança rigorosa: qualquer alteração acidental em fórmulas de saldo, tipos de movimentação, valores padrão de perfil ou relacionamentos entre empresas e setores será imediatamente bloqueada pela suíte de testes automatizados.
