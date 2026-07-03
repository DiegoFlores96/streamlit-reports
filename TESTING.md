# Guia de Testes

Testes automatizados usando **pytest** para validar funcionalidades de autenticação, JWT e controllers.

## 🚀 Executar Testes

### Instalar dependências:
```bash
pip install -r requirements.txt
```

### Rodar todos os testes:
```bash
pytest
```

### Rodar com cobertura:
```bash
pytest --cov=. --cov-report=html
```

Abra `htmlcov/index.html` no navegador para ver relatório detalhado de cobertura.

### Rodar testes específicos:
```bash
# Apenas JWT Helper
pytest tests/test_jwt_helper.py

# Apenas Login Controller
pytest tests/test_login_controller.py

# Apenas um teste
pytest tests/test_jwt_helper.py::TestJWTHelper::test_criar_token

# Modo verbose
pytest -v
```

### Rodar com markers:
```bash
# Testes unitários
pytest -m unit

# Testes de segurança
pytest -m security
```

## 📊 Estrutura

```
tests/
├── __init__.py
├── conftest.py                        # Fixtures e configuração
├── test_jwt_helper.py                 # Testes de JWT (10)
├── test_login_controller.py           # Testes de autenticação (15)
├── test_database_integration.py       # Integração com banco SQLite (15)
├── test_security_sql_injection.py     # Proteção contra SQL Injection (16)
├── test_controllers.py                # Controllers empresa/setor/dashboard (8)
├── test_empresa_setor_controller.py   # CRUD empresa e setor (8)
├── test_access_formatting.py          # Middleware e helpers de formato (16)
├── test_middleware_helpers.py         # Auth middleware e upload (7)
├── test_performance_e2e.py            # Performance, load e E2E (16)
└── test_smoke_perf.py                 # Smoke tests básicos (6)
```

## ✅ Cobertura Atual — 107 testes

- `helpers/jwt_helper.py`: Criação, validação e renovação de tokens (10 testes)
- `controller/loginController.py`: Hash/verificação de senha, registro, login (15 testes)
- `db/` + `model/`: Integração com banco de dados SQLite (15 testes)
  - Operações CRUD em TabEmpresa, TabUsuarios, TokenSessao, SetorDashboard
  - Testes de relacionamentos e constraints
  - Queries complexas (filtros, listagens)
- `controller/empresaController.py` + `setorController.py`: CRUD e validações (8 testes)
- `controller/dashboardController.py`: Mapeamento e sincronização de arquivos (8 testes)
- `middleware/access_control.py` + `middleware/auth.py`: Controle de acesso e sessão (7 testes)
- `helpers/formata.py` + `helpers/upload.py`: Formatação e upload de imagens (16 testes)
- Segurança — SQL Injection via SQLAlchemy ORM (16 testes)
- Performance e Load: hashing, consultas em massa, inserção em lote (16 testes)
- E2E smoke: fluxo criação→login, acesso admin, associação empresa↔usuário (parte dos 16 acima)

## 🎯 Testes Futuros

- [x] Testes de controllers (dashboard, empresa, setor)
- [x] Testes de middleware (access_control)
- [x] Testes de helpers (upload, formata, etc)
- [x] Testes E2E com Streamlit
- [x] Performance tests
- [x] Load tests

## 🔐 Cobertura de Segurança

Os testes validam:
- ✅ Senhas não salvas em plaintext
- ✅ Bcrypt com salt aleatório
- ✅ Compatibilidade com senhas legacy SHA256
- ✅ Política de senha forte (8+ chars, maiúscula, número)
- ✅ JWT com expiração
- ✅ Renovação de token

## 💡 Adicionando Novos Testes

1. Crie arquivo `tests/test_novo_modulo.py`
2. Importe o módulo a testar
3. Crie classe `TestNomeClasse`
4. Escreva métodos `test_descricao`

Exemplo:
```python
class TestMeuModulo:
    def test_funcionalidade(self):
        resultado = minha_funcao()
        assert resultado == esperado
```

## 📝 Convenções

- Nomes de testes começam com `test_`
- Testes descrevem o que estão testando
- Use `assert` para validações
- Use fixtures do `conftest.py` para dados comuns

## 🐛 Debugging

```bash
# Parar no primeiro erro
pytest -x

# Abrir debugger ao falhar
pytest --pdb

# Mostrar print statements
pytest -s
```

---

**Última atualização**: 2026-06-22 — 107 testes, todos passando ✅
