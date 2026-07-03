import os
import sys
import importlib
import subprocess
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import streamlit as st
import streamlit.components.v1 as components
from db.conexao import Conexao
from model.DashboardItem import DashboardItem
from model.SetorDashboard import SetorDashboard
from model.UsuarioDashboardAcesso import UsuarioDashboardAcesso


class DashboardController:
    def __init__(self):
        self.db = Conexao()
        # Mapeia a pasta física do seu projeto onde ficam as páginas
        self.caminho_base_dashboards = Path("views/pages/dashboard")

    def list_setores(self) -> list[SetorDashboard]:
        session = self.db.get_session()
        try:
            return session.query(SetorDashboard).order_by(SetorDashboard.nome_setor).all()
        finally:
            self.db.close_session(session)

    def sincronizar_arquivos_fisicos(self) -> tuple[bool, str]:
        """
        Varre 'views/pages/dashboard', cria os setores com base nas subpastas
        e insere os arquivos novos no banco de dados como Dashboards ativos,
        salvando o código da página sem a extensão do arquivo.
        """
        if not self.caminho_base_dashboards.exists():
            return False, f"Diretório físico não encontrado em: {self.caminho_base_dashboards}"

        session = self.db.get_session()
        arquivos_sincronizados = 0
        setores_criados = 0

        try:
            mapa_setores_banco = {s.nome_setor.lower().strip(): s.id_setor for s in session.query(SetorDashboard).all()}

            def _garantir_setor(nome_do_setor: str) -> int:
                nonlocal setores_criados
                nome_limpo = nome_do_setor.strip()
                chave = nome_limpo.lower()

                if chave in mapa_setores_banco:
                    return mapa_setores_banco[chave]

                novo_setor = SetorDashboard(nome_setor=nome_limpo, situacao="Ativado")
                session.add(novo_setor)
                session.flush()
                mapa_setores_banco[chave] = novo_setor.id_setor
                setores_criados += 1
                return novo_setor.id_setor

            codigos_existentes = {d.codigo_pagina.lower().strip() for d in session.query(DashboardItem).all()}

            # 1. PROCESSAR ARQUIVOS SOLTOS NA RAIZ (Setor: Geral)
            id_setor_geral = _garantir_setor("Geral")
            for arquivo in self.caminho_base_dashboards.glob("*.py"):
                if arquivo.name.startswith("__") or arquivo.stem in ["home", "app"]:
                    continue

                codigo_fmt = arquivo.stem.lower().strip()
                if codigo_fmt not in codigos_existentes:
                    novo_dash = DashboardItem(
                        nome_dashboard=arquivo.stem.replace("_", " ").title(),
                        descricao="Mapeado de forma automática da raiz do diretório de dashboards.",
                        tipo_pagina="dashboard",
                        codigo_pagina=codigo_fmt,
                        id_setor=id_setor_geral,
                        ativo=True
                    )
                    session.add(novo_dash)
                    codigos_existentes.add(codigo_fmt)
                    arquivos_sincronizados += 1

            # 2. PROCESSAR SUBPASTAS (Ex: estoque, comercial, etc.)
            for subpasta in self.caminho_base_dashboards.iterdir():
                if subpasta.is_dir() and not subpasta.name.startswith("__"):
                    nome_pasta_setor = subpasta.name.replace("_", " ").title()
                    id_setor_pasta = _garantir_setor(nome_pasta_setor)

                    for arquivo_sub in subpasta.glob("*.py"):
                        if arquivo_sub.name.startswith("__"):
                            continue

                        codigo_fmt = f"{subpasta.name}/{arquivo_sub.stem}".lower().strip()
                        if codigo_fmt not in codigos_existentes:
                            novo_dash = DashboardItem(
                                nome_dashboard=arquivo_sub.stem.replace("_", " ").title(),
                                descricao=f"Mapeado de forma automática da pasta do setor {nome_pasta_setor}.",
                                tipo_pagina="dashboard",
                                codigo_pagina=codigo_fmt,
                                id_setor=id_setor_pasta,
                                ativo=True
                            )
                            session.add(novo_dash)
                            codigos_existentes.add(codigo_fmt)
                            arquivos_sincronizados += 1

            session.commit()
            return True, f"Sincronização realizada! {setores_criados} novos setores criados e {arquivos_sincronizados} novas páginas adicionadas."

        except Exception as e:
            session.rollback()
            return False, f"Falha ao rodar scanner de arquivos: {str(e)}"
        finally:
            self.db.close_session(session)

    def obtener_arquivos_disponiveis(self) -> list[dict]:
        """Retorna a lista de todos os arquivos mantendo o caminho relativo sem a extensão."""
        if not self.caminho_base_dashboards.exists():
            return []

        arquivos_encontrados = []
        extensoes = ("*.py", "*.php", "*.html", "*.js")

        for ext in extensoes:
            for arquivo in self.caminho_base_dashboards.rglob(ext):
                if arquivo.name.startswith("__") or arquivo.stem in ["home", "app"]:
                    continue

                caminho_relativo = arquivo.relative_to(self.caminho_base_dashboards)

                if len(caminho_relativo.parts) > 1:
                    pasta_pai = "/".join(caminho_relativo.parts[:-1])
                    caminho_sem_extensao = f"{pasta_pai}/{arquivo.stem}"
                else:
                    caminho_sem_extensao = arquivo.stem

                arquivos_encontrados.append({
                    "caminho_final": caminho_sem_extensao.lower().strip(),
                    "nome_arquivo": arquivo.name
                })

        return sorted(arquivos_encontrados, key=lambda x: x["caminho_final"])

    def create_dashboard(self, nome_dashboard: str, descricao: str, id_setor: int, tipo_pagina: str = "dashboard",
                         codigo_pagina: str = "dashboard_exemplo") -> tuple[bool, str]:
        nome_dashboard = (nome_dashboard or "").strip()
        if not nome_dashboard:
            return False, "Informe o nome da página."

        session = self.db.get_session()
        try:
            dash = DashboardItem(
                nome_dashboard=nome_dashboard,
                descricao=(descricao or "").strip(),
                tipo_pagina=(tipo_pagina or "dashboard").strip().lower(),
                codigo_pagina=(codigo_pagina or "dashboard_exemplo").strip().lower(),
                id_setor=id_setor,
                ativo=True,
            )
            session.add(dash)
            session.commit()
            return True, "Página criada com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao criar página: {str(e)}"
        finally:
            self.db.close_session(session)

    def list_dashboards(self, active_only: bool = False) -> list[dict]:
        session = self.db.get_session()
        try:
            query = (
                session.query(
                    DashboardItem.id_dashboard,
                    DashboardItem.nome_dashboard,
                    DashboardItem.descricao,
                    DashboardItem.tipo_pagina,
                    DashboardItem.codigo_pagina,
                    DashboardItem.id_setor,
                    DashboardItem.ativo,
                    SetorDashboard.nome_setor,
                )
                .join(SetorDashboard, SetorDashboard.id_setor == DashboardItem.id_setor)
                .order_by(DashboardItem.nome_dashboard)
            )
            if active_only:
                query = query.filter(DashboardItem.ativo == True)

            rows = query.all()
            return [
                {
                    "id_dashboard": row.id_dashboard,
                    "nome_dashboard": row.nome_dashboard,
                    "descricao": row.descricao,
                    "tipo_pagina": row.tipo_pagina,
                    "codigo_pagina": row.codigo_pagina,
                    "id_setor": row.id_setor,
                    "ativo": bool(row.ativo),
                    "nome_setor": row.nome_setor,
                }
                for row in rows
            ]
        finally:
            self.db.close_session(session)

    def update_dashboard(self, id_dashboard: int, nome_dashboard: str, descricao: str, id_setor: int, tipo_pagina: str,
                         codigo_pagina: str, ativo: bool) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            dash = session.query(DashboardItem).filter_by(id_dashboard=id_dashboard).first()
            if not dash:
                return False, "Página não encontrada."

            dash.nome_dashboard = (nome_dashboard or "").strip()
            if not dash.nome_dashboard:
                return False, "Informe o nome da página."

            dash.descricao = (descricao or "").strip()
            dash.id_setor = id_setor
            dash.tipo_pagina = (tipo_pagina or "dashboard").strip().lower()
            dash.codigo_pagina = (codigo_pagina or "dashboard_exemplo").strip().lower()
            dash.ativo = bool(ativo)
            session.commit()
            return True, "Página actualizada com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao atualizar página: {str(e)}"
        finally:
            self.db.close_session(session)

    def deactivate_dashboard(self, id_dashboard: int) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            dash = session.query(DashboardItem).filter_by(id_dashboard=id_dashboard).first()
            if not dash:
                return False, "Página não encontrada."

            dash.ativo = False
            session.commit()
            return True, "Página desativada com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao desativar página: {str(e)}"
        finally:
            self.db.close_session(session)

    def get_user_allowed_dashboard_ids(self, id_usuario: int) -> list[int]:
        session = self.db.get_session()
        try:
            rows = session.query(UsuarioDashboardAcesso.id_dashboard).filter_by(id_usuario=id_usuario).all()
            return [r.id_dashboard for r in rows]
        finally:
            self.db.close_session(session)

    def grant_dashboard_access(self, id_usuario: int, dashboard_ids: list[int]) -> tuple[bool, str]:
        session = self.db.get_session()
        try:
            session.query(UsuarioDashboardAcesso).filter_by(id_usuario=id_usuario).delete()
            for id_dashboard in dashboard_ids:
                session.add(UsuarioDashboardAcesso(id_usuario=id_usuario, id_dashboard=id_dashboard))
            session.commit()
            return True, "Permissões atualizadas com sucesso."
        except Exception as e:
            session.rollback()
            return False, f"Erro ao atualizar permissões: {str(e)}"
        finally:
            self.db.close_session(session)

    def add_user_dashboard(self, id_usuario: int, id_dashboard: int) -> tuple[bool, str]:
        """Adiciona um dashboard individual à lista de acessos do usuário."""
        ids_atuais = self.get_user_allowed_dashboard_ids(id_usuario)
        if id_dashboard not in ids_atuais:
            ids_atuais.append(id_dashboard)
        return self.grant_dashboard_access(id_usuario, ids_atuais)

    def remove_user_dashboard(self, id_usuario: int, id_dashboard: int) -> tuple[bool, str]:
        """Remove um dashboard individual da lista de acessos do usuário."""
        ids_atuais = self.get_user_allowed_dashboard_ids(id_usuario)
        novos_ids = [x for x in ids_atuais if x != id_dashboard]
        return self.grant_dashboard_access(id_usuario, novos_ids)

    def renderizar_dashboard(self, codigo_pagina: str, login_controller) -> None:
        """
        Lê o código da página (ex: 'estoque/estoque' ou 'vendas'), descobre a extensão
        física real do arquivo (.py, .html, .php) e o renderiza de forma dinâmica.
        """
        codigo_limpo = (codigo_pagina or "").strip().lower()

        caminho_base_arquivo = self.caminho_base_dashboards / codigo_limpo
        pasta_do_dashboard = caminho_base_arquivo.parent
        nome_arquivo_puro = caminho_base_arquivo.name

        # -----------------------------------------------------------------
        # 1. ARQUIVO PYTHON (.py) - Carregamento por Caminho Físico Direto
        # -----------------------------------------------------------------
        arquivo_py = caminho_base_arquivo.with_suffix(".py")
        if arquivo_py.exists():
            try:
                # Cria uma chave única para registrar o arquivo na memória do Python
                nome_modulo_unico = f"dinamico_{codigo_limpo.replace('/', '_')}"

                # Lê a especificação do arquivo diretamente, sem depender de pacotes de pontos ou __init__.py
                spec = spec_from_file_location(nome_modulo_unico, str(arquivo_py))
                modulo = module_from_spec(spec)
                sys.modules[nome_modulo_unico] = modulo
                spec.loader.exec_module(modulo)

                # Executa a função padrão do dashboard
                if hasattr(modulo, "render_page"):
                    modulo.render_page(login_controller)
                elif hasattr(modulo, f"render_{nome_arquivo_puro}_page"):
                    funcao = getattr(modulo, f"render_{nome_arquivo_puro}_page")
                    funcao(login_controller)
                else:
                    st.error(
                        f"❌ Função 'render_page' ou 'render_{nome_arquivo_puro}_page' não encontrada em '{arquivo_py.name}'.")
            except Exception as e:
                st.error(f"💥 Erro ao executar o módulo Python ({arquivo_py.name}): {e}")
            return

        # -----------------------------------------------------------------
        # 2. ARQUIVO HTML / JAVASCRIPT (.html)
        # -----------------------------------------------------------------
        arquivo_html = caminho_base_arquivo.with_suffix(".html")
        if not arquivo_html.exists() and (pasta_do_dashboard / "index.html").exists():
            arquivo_html = pasta_do_dashboard / "index.html"

        if arquivo_html.exists():
            try:
                html_content = open(arquivo_html, "r", encoding="utf-8").read()

                arquivo_js = pasta_do_dashboard / "script.js"
                if not arquivo_js.exists():
                    arquivo_js = caminho_base_arquivo.with_suffix(".js")

                if arquivo_js.exists():
                    js_content = open(arquivo_js, "r", encoding="utf-8").read()
                    html_content += f"\n<script>\n{js_content}\n</script>"

                components.html(html_content, height=750, scrolling=True)
            except Exception as e:
                st.error(f"❌ Erro ao ler os arquivos HTML/JS: {e}")
            return

        # -----------------------------------------------------------------
        # 3. ARQUIVO PHP (.php)
        # -----------------------------------------------------------------
        arquivo_php = caminho_base_arquivo.with_suffix(".php")
        if arquivo_php.exists():
            try:
                resultado = subprocess.run(
                    ["php", str(arquivo_php)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8"
                )
                if resultado.returncode == 0:
                    components.html(resultado.stdout, height=750, scrolling=True)
                else:
                    st.error("❌ Erro interno de execução no script PHP:")
                    st.code(resultado.stderr)
            except FileNotFoundError:
                st.error("🖥️ Ambiente PHP não detectado ou indisponível no PATH do servidor.")
            except Exception as e:
                st.error(f"❌ Erro no processamento do PHP: {e}")
            return

        st.error(f"📂 Arquivo ou subpasta correspondente ao código '{codigo_limpo}' não foi mapeado fisicamente.")