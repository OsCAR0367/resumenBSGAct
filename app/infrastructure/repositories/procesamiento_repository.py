import logging
from typing import Optional
from app.infrastructure.db_sql_server.sql_server_client_async import SQLServerClientAsync

logger = logging.getLogger(__name__)

class ProcesamientoRepository:
    def __init__(self, db: SQLServerClientAsync):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. Crear Sesión
    # -------------------------------------------------------------------------
    async def create_sesion_online(self, data: dict) -> int:
        try:
            # CAMBIO: Sintaxis ODBC con '?' en lugar de ':param'
            # NOTA: aioodbc requiere que los parámetros se pasen en orden exacto.
            sql = """
                DECLARE @new_id int;
                EXEC ia.SP_TProcesamientoSesionOnline_Insertar
                    @IdPEspecificoSesion = ?,
                    @Sesion = ?,
                    @Usuario = ?,
                    @NewId = @new_id OUTPUT;
                SELECT @new_id as Id;
            """
            
            params = [
                data.get("IdPEspecificoSesion"), 
                data.get("Sesion", "Sesion Default"),
                data.get("Usuario", "System")
            ]

            # Usamos fetch_one porque esperamos el 'SELECT @new_id' del final
            row = await self.db.fetch_one(sql, params)
            
            # Tu cliente devuelve un diccionario {col: val}
            if row and row.get("Id"):
                return row["Id"]
                
            # Fallback por si acaso devuelve tupla o el nombre difiere
            if row: 
                return list(row.values())[0]
                
            raise ValueError("SP de Sesión no retornó ID")

        except Exception as e:
            logger.error(f"Error creando sesión: {e}")
            raise e

    # -------------------------------------------------------------------------
    # 2. Crear Detalle de Etapa
    # -------------------------------------------------------------------------
    async def create_detalle_etapa(self, sesion_id: int, etapa_id: int, usuario: str = "System") -> int:
        try:
            sql = """
                DECLARE @out int;
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_Insertar
                    @IdProcesamientoSesionOnline = ?,
                    @IdEtapaProcesamientoSesion = ?,
                    @Usuario = ?,
                    @IdDetalleSalida = @out OUTPUT;
                SELECT @out as Id;
            """
            params = [sesion_id, etapa_id, usuario]
            
            row = await self.db.fetch_one(sql, params)
            
            if row and row.get("Id"):
                return row["Id"]
            if row: 
                return list(row.values())[0]
                
            raise ValueError("Error creando detalle etapa")

        except Exception as e:
            logger.error(f"Error creando detalle etapa: {e}")
            raise e

    # -------------------------------------------------------------------------
    # 3. Actualizar Estado de Detalle
    # -------------------------------------------------------------------------
    async def update_detalle_estado(self, detalle_id: int, estado_id: int, resultado: str, nro_errores: int = 0, usuario: str = "System"):
        try:
            sql = """
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_ActualizarEstado
                    @IdDetalleProcesamiento = ?,
                    @IdEstadoNuevo = ?,
                    @Resultado = ?,
                    @NroErrores = ?,
                    @Usuario = ?
            """
            params = [detalle_id, estado_id, resultado, nro_errores, usuario]
            
            # Usamos execute_non_query para operaciones sin retorno de filas
            await self.db.execute_non_query(sql, params)
            
        except Exception as e:
            logger.error(f"Error actualizando estado: {e}")
            raise e

    # -------------------------------------------------------------------------
    # 4. Actualizar Resumen
    # -------------------------------------------------------------------------
    async def update_summarization(self, sesion_id: int, success: bool, summary_text: str):
        try:
            sql = """
                EXEC ia.SP_TProcesamientoSesionOnline_ActualizarResumen
                    @Id = ?,
                    @Resumen = ?,
                    @TextoResumen = ?
            """
            # SQL Server BIT: 1 o 0
            flag = 1 if success else 0
            params = [sesion_id, flag, summary_text]
            
            await self.db.execute_non_query(sql, params)
            
        except Exception as e:
            logger.error(f"Error actualizando resumen: {e}")
            raise e