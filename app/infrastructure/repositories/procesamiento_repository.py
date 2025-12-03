import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

logger = logging.getLogger(__name__)

class ProcesamientoRepository:
    """
    Repositorio encargado de la persistencia del flujo de procesamiento.
    Maneja la Tabla Maestra (SesionOnline) y sus Detalles (Etapas).
    """

    def __init__(self, db: Session):
        self.db = db

    # -------------------------------------------------------------------------
    # 1. GESTIÓN DE SESIÓN (La entidad "Padre")
    # SP: ia.SP_TProcesamientoSesionOnline_Insertar
    # -------------------------------------------------------------------------
    def create_sesion_online(self, data: dict) -> int:
        """
        Crea una nueva sesión de procesamiento o retorna error si falla.
        Mapea al SP que definiste para insertar T_ProcesamientoSesionOnline.
        """
        try:
            # Usamos sintaxis DECLARE para capturar el parámetro OUTPUT de SQL Server
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
                "nombre_sesion": data.get("Sesion", "Sesion Sin Nombre"),
                "usuario": data.get("Usuario", "System")
            }

            # Ejecutar y obtener el escalar
            result = self.db.execute(sql, params).fetchone()
            self.db.commit()
            
            if result and result[0]:
                created_id = result[0]
                logger.info(f"Sesión creada exitosamente. ID: {created_id}")
                return created_id
            
            raise ValueError("El SP de creación de sesión no retornó un ID.")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en create_sesion_online: {e}")
            raise e

    # -------------------------------------------------------------------------
    # 2. GESTIÓN DE ETAPAS (Los "Hijos": Video, Audio, Transcripción...)
    # SP: ia.SP_TDetalleProcesamientoSesionOnline_Insertar
    # -------------------------------------------------------------------------
    def create_detalle_etapa(self, sesion_id: int, etapa_id: int, usuario: str = "System") -> int:
        """
        Registra el inicio de una etapa (Estado 2: En Proceso).
        Retorna el ID del detalle creado para poder actualizarlo luego.
        """
        try:
            sql = text("""
                DECLARE @out_detalle_id int;
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_Insertar
                    @IdProcesamientoSesionOnline = :sesion_id,
                    @IdEtapaProcesamientoSesion = :etapa_id,
                    @Usuario = :usuario,
                    @IdDetalleSalida = @out_detalle_id OUTPUT;
                SELECT @out_detalle_id;
            """)

            params = {
                "sesion_id": sesion_id,
                "etapa_id": etapa_id,
                "usuario": usuario
            }

            result = self.db.execute(sql, params).fetchone()
            self.db.commit()

            if result and result[0]:
                detalle_id = result[0]
                logger.info(f"Etapa {etapa_id} iniciada para Sesión {sesion_id}. DetalleID: {detalle_id}")
                return detalle_id
            
            raise ValueError(f"No se pudo crear el detalle para la etapa {etapa_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en create_detalle_etapa (Sesión {sesion_id}, Etapa {etapa_id}): {e}")
            raise e

    # -------------------------------------------------------------------------
    # 3. ACTUALIZACIÓN DE ESTADO (Finalizar Etapa)
    # SP: ia.SP_TDetalleProcesamientoSesionOnline_ActualizarEstado
    # -------------------------------------------------------------------------
    def update_detalle_estado(self, detalle_id: int, estado_nuevo_id: int, resultado: str, nro_errores: int = 0, usuario: str = "System"):
        """
        Actualiza el estado de una etapa específica.
        Estados comunes: 3 (Completado), 4 (Error).
        """
        try:
            sql = text("""
                EXEC ia.SP_TDetalleProcesamientoSesionOnline_ActualizarEstado
                    @IdDetalleProcesamiento = :detalle_id,
                    @IdEstadoNuevo = :estado_id,
                    @Resultado = :texto_resultado,
                    @NroErrores = :errores,
                    @Usuario = :usuario
            """)

            params = {
                "detalle_id": detalle_id,
                "estado_id": estado_nuevo_id,
                "texto_resultado": resultado or "",
                "errores": nro_errores,
                "usuario": usuario
            }

            self.db.execute(sql, params)
            self.db.commit()
            logger.debug(f"Detalle {detalle_id} actualizado a Estado {estado_nuevo_id}.")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en update_detalle_estado (Detalle {detalle_id}): {e}")
            raise e

    # -------------------------------------------------------------------------
    # 4. ACTUALIZACIÓN DE RESUMEN (Específico para SummarizationService)
    # SP: ia.SP_TProcesamientoSesionOnline_ActualizarResumen (Del código original)
    # -------------------------------------------------------------------------
    def update_summarization(self, sesion_id: int, success: bool, summary_text: str):
        """
        Actualiza el campo de resumen en la tabla principal.
        """
        try:
            # Nota: Asegúrate de que este SP exista en tu BD. 
            # Si no existe, deberás crearlo o hacer un UPDATE directo a la tabla T_ProcesamientoSesionOnline.
            sql = text("""
                EXEC ia.SP_TProcesamientoSesionOnline_ActualizarResumen
                    @Id = :id,
                    @Resumen = :flag_resumen,
                    @TextoResumen = :texto
            """)
            
            params = {
                "id": sesion_id,
                "flag_resumen": 1 if success else 0,
                "texto": summary_text or ""
            }
            
            self.db.execute(sql, params)
            self.db.commit()
            logger.info(f"Resumen guardado en BD para Sesión {sesion_id}")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error en update_summarization (Sesión {sesion_id}): {e}")
            raise e