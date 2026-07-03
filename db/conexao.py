import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from model.TabUsuarios import Base
from model.DashboardItem import DashboardItem  # noqa: F401
from model.SetorDashboard import SetorDashboard  # noqa: F401
from model.UsuarioDashboardAcesso import UsuarioDashboardAcesso  # noqa: F401
from model.UsuarioSetorAcesso import UsuarioSetorAcesso  # noqa: F401
from model.TokenSessao import TokenSessao  # noqa: F401

load_dotenv()


class Conexao:
    _instance = None
    _engine = None
    _session_maker = None

    @staticmethod
    def _clean_env(value: str | None, default: str = "") -> str:
        if value is None:
            return default
        value = value.strip().strip('"').strip("'")
        return value or default

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Conexao, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is None:
            self._init_db()

    def _init_db(self):
        database_url = self._clean_env(os.getenv("DATABASE_URL"))
        db_file_env = self._clean_env(os.getenv("DB_FILE"), "reports.db")

        if database_url:
            db_url = database_url
        else:
            db_file = Path(db_file_env).resolve()
            db_url = f"sqlite:///{db_file}"

        try:
            self._engine = create_engine(
                db_url,
                echo=False,
                connect_args={"timeout": 30, "check_same_thread": False},
                poolclass=NullPool,
            )

            self._session_maker = sessionmaker(bind=self._engine)

            # Cria as tabelas se não existirem
            Base.metadata.create_all(self._engine)
            self._run_migrations()
        except Exception as e:
            print(f"Erro ao conectar ao banco de dados: {e}")
            raise

    def _run_migrations(self):
        with self._engine.begin() as conn:
            # ========== MIGRAÇÕES EXISTENTES ==========
            cols = conn.execute(text("PRAGMA table_info('Tabcad_usuarios')")).fetchall()
            col_names = {col[1] for col in cols}
            if "perfil" not in col_names:
                conn.execute(text("ALTER TABLE Tabcad_usuarios ADD COLUMN perfil TEXT DEFAULT 'Padrao'"))

            # Garante estrutura de setores e migra dados legados se existirem.
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS Tabcad_setor
                    (
                        id_setor
                        INTEGER
                        PRIMARY
                        KEY
                        AUTOINCREMENT,
                        nome_setor
                        TEXT,
                        situacao
                        TEXT
                        DEFAULT
                        'Ativado',
                        dt_criacao
                        TEXT,
                        dt_ultima_atualizacao
                        TEXT,
                        dt_desativacao
                        TEXT
                    )
                    """
                )
            )

            temas_exists = conn.execute(
                text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='Tabcad_temas_dashboard'"
                )
            ).fetchone()

            setor_count = conn.execute(text("SELECT COUNT(*) FROM Tabcad_setor")).scalar() or 0
            if temas_exists and setor_count == 0:
                conn.execute(
                    text(
                        """
                        INSERT INTO Tabcad_setor (id_setor, nome_setor, situacao)
                        SELECT id_tema, nome_tema, COALESCE(situacao, 'Ativado')
                        FROM Tabcad_temas_dashboard
                        """
                    )
                )

            dash_cols = conn.execute(text("PRAGMA table_info('Tabcad_dashboards')")).fetchall()
            dash_col_names = {col[1] for col in dash_cols}
            if "tipo_pagina" not in dash_col_names:
                conn.execute(text("ALTER TABLE Tabcad_dashboards ADD COLUMN tipo_pagina TEXT DEFAULT 'dashboard'"))
            if "codigo_pagina" not in dash_col_names:
                conn.execute(
                    text("ALTER TABLE Tabcad_dashboards ADD COLUMN codigo_pagina TEXT DEFAULT 'dashboard_exemplo'"))
            if "id_setor" not in dash_col_names:
                conn.execute(text("ALTER TABLE Tabcad_dashboards ADD COLUMN id_setor INTEGER"))
            if "id_tema" in dash_col_names:
                conn.execute(text("UPDATE Tabcad_dashboards SET id_setor = id_tema WHERE id_setor IS NULL"))

                # Recria a tabela de dashboards sem a coluna legada id_tema.
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS Tabcad_dashboards_new
                        (
                            id_dashboard
                            INTEGER
                            PRIMARY
                            KEY
                            AUTOINCREMENT,
                            nome_dashboard
                            VARCHAR
                        (
                            140
                        ) NOT NULL,
                            descricao VARCHAR
                        (
                            255
                        ),
                            id_setor INTEGER NOT NULL,
                            ativo BOOLEAN,
                            tipo_pagina TEXT DEFAULT 'dashboard',
                            codigo_pagina TEXT DEFAULT 'dashboard_exemplo'
                            )
                        """
                    )
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO Tabcad_dashboards_new (id_dashboard, nome_dashboard, descricao, id_setor, ativo,
                                                           tipo_pagina, codigo_pagina)
                        SELECT id_dashboard,
                               nome_dashboard,
                               descricao,
                               COALESCE(id_setor, id_tema),
                               COALESCE(ativo, 1),
                               COALESCE(tipo_pagina, 'dashboard'),
                               COALESCE(codigo_pagina, 'dashboard_exemplo')
                        FROM Tabcad_dashboards
                        """
                    )
                )
                conn.execute(text("DROP TABLE Tabcad_dashboards"))
                conn.execute(text("ALTER TABLE Tabcad_dashboards_new RENAME TO Tabcad_dashboards"))
                conn.execute(text("PRAGMA foreign_keys=ON"))

            # Remove tabela legada de temas após garantir cópia em Tabcad_setor.
            legacy_temas_exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name='Tabcad_temas_dashboard'")
            ).fetchone()
            if legacy_temas_exists:
                conn.execute(
                    text(
                        """
                        INSERT
                        OR IGNORE INTO Tabcad_setor (id_setor, nome_setor, situacao)
                        SELECT id_tema, nome_tema, COALESCE(situacao, 'Ativado')
                        FROM Tabcad_temas_dashboard
                        """
                    )
                )
                conn.execute(text("PRAGMA foreign_keys=OFF"))
                conn.execute(text("DROP TABLE IF EXISTS Tabcad_temas_dashboard"))
                conn.execute(text("PRAGMA foreign_keys=ON"))

            # ========== NOVA MIGRAÇÃO: TABELA DE TOKENS ==========
            # Criar tabela de tokens de sessão
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS Tabcad_token_sessao
                    (
                        id_token
                        INTEGER
                        PRIMARY
                        KEY
                        AUTOINCREMENT,
                        id_usuario
                        INTEGER
                        NOT
                        NULL,
                        token
                        TEXT
                        NOT
                        NULL
                        UNIQUE,
                        dt_criacao
                        INTEGER
                        NOT
                        NULL,
                        dt_expiracao
                        INTEGER,
                        dt_ultimo_acesso
                        INTEGER,
                        ativo
                        BOOLEAN
                        DEFAULT
                        1
                    )
                    """
                )
            )
            # Criar tabela de empresas
            conn.execute(
                text(
                 """CREATE TABLE IF NOT EXISTS Tabcad_empresas (
                        id_empresa INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome VARCHAR(200) NOT NULL DEFAULT 'Minha Empresa',
                        cnpj VARCHAR(18) UNIQUE,
                        razao_social VARCHAR(200),
                        email VARCHAR(200),
                        telefone VARCHAR(20),
                        endereco VARCHAR(500),
                        cidade VARCHAR(100),
                        estado VARCHAR(2),
                        cep VARCHAR(10),
                        logo TEXT,
                        tema_primario VARCHAR(20) DEFAULT '#1f2937',
                        tema_secundario VARCHAR(20) DEFAULT '#2563eb',
                        sidebar_fundo VARCHAR(20) DEFAULT '#fafafa',
                        sidebar_texto VARCHAR(20) DEFAULT '#1f2937',
                        ativo BOOLEAN DEFAULT 1,
                        dt_criacao INTEGER,
                        dt_atualizacao INTEGER,
                        cor_alerta_vermelho VARCHAR(20) DEFAULT '#1f2937',
                        cor_alerta_amarelo VARCHAR(20) DEFAULT '#2563eb',
                        cor_alerta_verde VARCHAR(20) DEFAULT '#059669"'
                    );"""
                )
            )

            # Adicionar coluna id_empresa na tabela de usuários se não existir
            cols_usuarios = conn.execute(text("PRAGMA table_info('Tabcad_usuarios')")).fetchall()
            col_names_usuarios = {col[1] for col in cols_usuarios}
            if "id_empresa" not in col_names_usuarios:
                conn.execute(text(
                    "ALTER TABLE Tabcad_usuarios ADD COLUMN id_empresa INTEGER REFERENCES Tabcad_empresas(id_empresa)"))
            # Criar índices para melhor performance
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_token_sessao_token ON Tabcad_token_sessao(token)"))
            conn.execute(
                text("CREATE INDEX IF NOT EXISTS idx_token_sessao_usuario ON Tabcad_token_sessao(id_usuario, ativo)"))

            # Verificar se precisa adicionar coluna jwt_token na sessão (opcional)
            # Isso é apenas para referência, não é uma coluna de banco

    def get_engine(self):
        return self._engine

    def get_session(self) -> Session:
        return self._session_maker()

    def close_session(self, session: Session):
        if session:
            session.close()