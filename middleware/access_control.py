class AccessControlMiddleware:
    @staticmethod
    def require_admin(login_controller) -> bool:
        # Apenas usuários com perfil Admin podem ver a área administrativa.
        return login_controller.is_admin()

    @staticmethod
    def get_allowed_pages(login_controller):
        # Busca as páginas liberadas para montar o menu do usuário.
        return login_controller.get_menu_pages_for_logged_user()
