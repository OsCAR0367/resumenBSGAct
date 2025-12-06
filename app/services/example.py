from app.core.setup_config import settings
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync
from app.infrastructure.repositories import ChatPortalRepository

from app.core.setup_logging import logger

class ChatPortalService:
    """
        Repositorio para realizar operaciones CRUD sobre la tabla 'chat_portal'.
        La conexión a la base de datos es recibida desde el servicio que use este repositorio.
    """

    def __init__(self):
        self.dsn = settings.get_database_sql_server_url()
        self.repositorio: ChatPortalRepository | None = None

    def asignar_db_repositorio(self, db: SQLServerClientAsync):
        self.repositorio = ChatPortalRepository(db)

    async def obt_chats_portal(self):
        async with SQLServerClientAsync(dsn=self.dsn) as db:
            self.asignar_db_repositorio(db)
            usuarios_activos = await self.repositorio.obt_chats_portal()
            return usuarios_activos

    async def obt_chat_portal(self, id_chat: int):
        async with SQLServerClientAsync(dsn=self.dsn) as db:
            self.asignar_db_repositorio(db)
            usuario_activo = await self.repositorio.obt_chat_portal(id_chat=id_chat)
            return usuario_activo

    async def act_chat_portal_estado(self):
        async with SQLServerClientAsync(dsn=self.dsn) as db:
            self.asignar_db_repositorio(db)
            try:
                async with db.transaction():
                    await self.repositorio.act_chat_portal_estado(5, 1)
                    await self.repositorio.act_chat_portal_estado(6, 1)

            except Exception as exc:
                # Si ocurre una excepción dentro del bloque, se hace ROLLBACK automáticamente
                logger.error("Error en la transacción de ejemplo: %s", exc)
                raise