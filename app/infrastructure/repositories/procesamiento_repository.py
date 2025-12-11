import logging
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync

logger = logging.getLogger(__name__)

class ProcesamientoRepository:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db

    async def create_sesion_online(self, data: dict) -> int:
        try:
            sql = """
                DECLARE @new_id int;
                EXEC ia.SP_TProcesamientoSesionOnline_Insertar
                    @IdPEspecificoSesion = ?, @Sesion = ?, @UrlVideo = ?, @Usuario = ?, @NewId = @new_id OUTPUT;
                SELECT @new_id as Id;
            """
            params = [
                data.get("IdPEspecificoSesion"), 
                data.get("Sesion", "Sesion Default"),
                data.get("UrlVideo", ""),
                data.get("Usuario", "System")
            ]
            row = await self.db.fetch_one(sql, params)
            if row: return int(list(row.values())[0])
            raise ValueError("SP no retornó ID")
        except Exception as e:
            logger.error(f"Error creando sesión: {e}")
            raise e

    async def create_detalle_etapa(self, sesion_id: int, etapa_id: int, usuario: str = "System") -> int:
        try:
            sql = """
                DECLARE @out int;
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_Insertar
                    @IdProcesamientoSesionOnline = ?, @IdEtapaProcesamientoSesion = ?, @Usuario = ?, @IdDetalleSalida = @out OUTPUT;
                SELECT @out as Id;
            """
            row = await self.db.fetch_one(sql, [sesion_id, etapa_id, usuario])
            if row: return int(list(row.values())[0])
            raise ValueError("Error creando detalle")
        except Exception as e:
            logger.error(f"Error creando detalle: {e}")
            raise e

    async def update_detalle_estado(self, detalle_id: int, estado_id: int, resultado: str, nro_errores: int = 0, usuario: str = "System"):
        """
        Este es el método genérico. 'resultado' guardará el Texto del Resumen, 
        el Guion o lo que retorne la etapa.
        """
        try:
            sql = """
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_ActualizarEstado
                    @IdDetalleProcesamiento = ?, @IdEstadoNuevo = ?, @Resultado = ?, @NroErrores = ?, @Usuario = ?
            """
            # Nos aseguramos que resultado sea string
            res_str = str(resultado) if resultado is not None else ""
            await self.db.execute_non_query(sql, [detalle_id, estado_id, res_str, nro_errores, usuario])
        except Exception as e:
            logger.error(f"Error actualizando estado: {e}")
            raise e

    async def insert_tipo_generar(self, sesion_id: int, tipo_id: int) -> int:
        try:
            sql = """
                DECLARE @out int;
                EXEC ia.SP_TProcesamientoTipoGenerar_Insertar
                    @IdProcesamientoSesionOnline = ?, @IdResumenGrabacionOnline = ?, @Usuario = 'System', @NewId = @out OUTPUT;
                SELECT @out as Id;
            """
            row = await self.db.fetch_one(sql, [sesion_id, tipo_id])
            if row: return int(list(row.values())[0])
            return 0
        except Exception as e:
            logger.error(f"Error insertando tipo generar: {e}")
            raise e

    async def update_tipo_generar(self, tipo_generar_id: int, url: str, realizado: bool):
        try:
            sql = """
                EXEC ia.SP_TProcesamientoTipoGenerar_ActualizarTipoGenerar
                    @Id = ?, @RegistroUrl = ?, @Usuario = 'System'
            """
            await self.db.execute_non_query(sql, [tipo_generar_id, url])
        except Exception as e:
            logger.error(f"Error actualizando entregable: {e}")
            raise e