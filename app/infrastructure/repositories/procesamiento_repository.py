import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ProcesamientoRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. Crear Sesión
    # -------------------------------------------------------------------------
    async def create_sesion_online(self, data: dict) -> int:
        try:
            # CORRECCIÓN: Se eliminó @UrlVideo y se usa @Usuario
            sql = text("""
                DECLARE @new_id int;
                EXEC ia.SP_TProcesamientoSesionOnline_Insertar
                    @IdPEspecificoSesion = :id_especifico,
                    @Sesion = :nombre_sesion,
                    @Usuario = :usuario,
                    @NewId = @new_id OUTPUT;
                SELECT @new_id;
            """)
            
            params = {
                "id_especifico": data.get("IdPEspecificoSesion"), 
                "nombre_sesion": data.get("Sesion", "Sesion Default"),
                # "url_video": data.get("UrlVideo"), <-- NO SE ENVÍA A LA BD
                "usuario": data.get("Usuario", "System")
            }

            # Ejecución nativa asíncrona
            result = await self.db.execute(sql, params)
            row = result.fetchone()
            await self.db.commit()
            
            if row and row[0]:
                return row[0]
            raise ValueError("SP de Sesión no retornó ID")

        except Exception as e:
            await self.db.rollback()
            raise e

    # -------------------------------------------------------------------------
    # 2. Crear Detalle de Etapa
    # -------------------------------------------------------------------------
    async def create_detalle_etapa(self, sesion_id: int, etapa_id: int, usuario: str = "System") -> int:
        try:
            # Se usa @Usuario según tu definición
            sql = text("""
                DECLARE @out int;
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_Insertar
                    @IdProcesamientoSesionOnline = :sesion_id,
                    @IdEtapaProcesamientoSesion = :etapa_id,
                    @Usuario = :usuario,
                    @IdDetalleSalida = @out OUTPUT;
                SELECT @out;
            """)
            params = {
                "sesion_id": sesion_id, 
                "etapa_id": etapa_id, 
                "usuario": usuario
            }
            
            result = await self.db.execute(sql, params)
            row = result.fetchone()
            await self.db.commit()
            
            if row and row[0]:
                return row[0]
            raise ValueError("Error creando detalle etapa")

        except Exception as e:
            await self.db.rollback()
            raise e

    # -------------------------------------------------------------------------
    # 3. Actualizar Estado de Detalle
    # -------------------------------------------------------------------------
    async def update_detalle_estado(self, detalle_id: int, estado_id: int, resultado: str, nro_errores: int = 0, usuario: str = "System"):
        try:
            # Se usa @Usuario según tu definición
            sql = text("""
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_ActualizarEstado
                    @IdDetalleProcesamiento = :d_id,
                    @IdEstadoNuevo = :e_id,
                    @Resultado = :res,
                    @NroErrores = :err,
                    @Usuario = :user
            """)
            params = {
                "d_id": detalle_id, 
                "e_id": estado_id, 
                "res": resultado, 
                "err": nro_errores, 
                "user": usuario
            }
            await self.db.execute(sql, params)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    # -------------------------------------------------------------------------
    # 4. Actualizar Resumen (Este SP debe existir en tu BD para el paso final)
    # -------------------------------------------------------------------------
    async def update_summarization(self, sesion_id: int, success: bool, summary_text: str):
        try:
            sql = text("""
                EXEC ia.SP_TProcesamientoSesionOnline_ActualizarResumen
                    @Id = :id,
                    @Resumen = :flag,
                    @TextoResumen = :txt
            """)
            params = {
                "id": sesion_id, 
                "flag": 1 if success else 0, 
                "txt": summary_text
            }
            await self.db.execute(sql, params)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e