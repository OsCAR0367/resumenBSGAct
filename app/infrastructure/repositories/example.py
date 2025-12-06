from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync


class ChatPortalRepository:
    """
        Repositorio para realizar operaciones CRUD sobre la tabla 'chat_portal'.
        La conexión a la base de datos es recibida desde el servicio que use este repositorio.
    """

    def __init__(self, connection: SQLServerClientAsync):
        self.db = connection

    async def obt_chats_portal(self):
        return await self.db.fetch_all(
            "SELECT TOP 50 * FROM ia.T_ChatbotPortalHiloChat WHERE Estado = ?",
            params=[1]
        )

    async def obt_chat_portal(self, id_chat: int):
        return await self.db.fetch_one(
            "SELECT TOP 1 * FROM ia.T_ChatbotPortalHiloChat WHERE Id = ?",
            params=[id_chat],
        )

    async def act_chat_portal_estado(self, id_chat: int, estado: int):
        await self.db.execute_non_query(
            "UPDATE ia.T_ChatbotPortalHiloChat SET Estado = ? WHERE Id = ?",
            params=[estado, id_chat],
        )