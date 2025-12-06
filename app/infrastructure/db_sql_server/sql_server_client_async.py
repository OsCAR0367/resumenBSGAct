import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Sequence, AsyncIterator

import aioodbc

from app.core.setup_config import settings
from app.core.setup_logging import logger


class SQLServerClientAsync:
    """
    Cliente asíncrono simple para SQL Server utilizando aioodbc, sin uso de pools.

    Esta clase encapsula:
    - Conexión y cierre explícitos (`connect` / `close`).
    - Uso como async context manager (`async with SQLServerClientAsync(...)`).
    - Consultas SELECT (`fetch_one`, `fetch_all`).
    - Ejecución de operaciones de modificación (`execute_non_query`).
    - Manejo explícito de transacciones (BEGIN/COMMIT/ROLLBACK) y
      un context manager de transacción (`transaction`).

    NOTA:
    - Los parámetros de las consultas usan el estilo de placeholders `?`,
      propio de ODBC/pyodbc.
    """

    def __init__(
        self,
        dsn: str,
        *,
        autocommit: bool = True,
        timeout: Optional[float] = 10,
    ) -> None:
        """
        Inicializa el cliente sin abrir aún la conexión.

        Args:
            dsn: Cadena DSN o connection string ODBC para SQL Server.
            autocommit: Valor por defecto de autocommit para la conexión.
            timeout: Tiempo máximo (en segundos) para establecer la conexión.
        """
        self._dsn = dsn
        self._autocommit_default = autocommit
        self._timeout = timeout

        self._conn: Optional[aioodbc.Connection] = None
        self._in_transaction: bool = False

    # -------------------------------------------------------------------------
    # Gestión de conexión
    # -------------------------------------------------------------------------
    async def connect(self) -> None:
        """
        Abre la conexión a la base de datos si aún no está abierta.
        """
        if self._conn is not None:
            return

        logger.info("Abriendo conexión a SQL Server")
        try:
            self._conn = await aioodbc.connect(
                dsn=self._dsn,
                autocommit=self._autocommit_default,
                timeout=self._timeout,
            )
            logger.info("Conexión establecida correctamente")
        except Exception:
            logger.exception("Error al abrir la conexión a SQL Server")
            raise

    async def close(self) -> None:
        """
        Cierra la conexión a la base de datos si está abierta.
        """
        if self._conn is None:
            return

        logger.info("Cerrando conexión a SQL Server")
        try:
            await self._conn.close()
        except Exception:
            logger.exception("Error al cerrar la conexión a SQL Server")
            raise
        finally:
            self._conn = None
            self._in_transaction = False
            logger.info("Conexión cerrada")

    def _ensure_connected(self) -> aioodbc.Connection:
        """
        Obtiene la conexión actual o lanza una excepción si no está abierta.
        """
        if self._conn is None:
            raise RuntimeError(
                "La conexión no está inicializada. Llama a 'await connect()' "
                "o usa el cliente con 'async with'."
            )
        return self._conn

    # -------------------------------------------------------------------------
    # Soporte para async context manager
    # -------------------------------------------------------------------------
    async def __aenter__(self) -> "SQLServerClientAsync":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # -------------------------------------------------------------------------
    # Consultas de solo lectura
    # -------------------------------------------------------------------------
    async def fetch_all(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Ejecuta un SELECT y retorna todas las filas como lista de diccionarios.

        Args:
            query: Consulta SQL con placeholders `?` para parámetros.
            params: Secuencia de parámetros posicionales (opcional).

        Returns:
            Lista de diccionarios, donde cada diccionario representa una fila.
        """
        conn = self._ensure_connected()
        params = list(params) if params is not None else []

        logger.info("Ejecutando fetch_all: %s | params=%s", query, params)

        cursor = await conn.cursor()
        try:
            await cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            rows = await cursor.fetchall()

            result: List[Dict[str, Any]] = [
                {col: value for col, value in zip(columns, row)} for row in rows
            ]

            logger.info("fetch_all completado: %d filas", len(result))
            return result

        except Exception:
            logger.exception("Error ejecutando fetch_all: %s", query)
            raise
        finally:
            await cursor.close()

    async def fetch_one(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Ejecuta un SELECT que se espera retorne como máximo una fila.

        Args:
            query: Consulta SQL con placeholders `?`.
            params: Secuencia de parámetros posicionales (opcional).

        Returns:
            Un diccionario con la fila o None si no hay resultados.
        """
        conn = self._ensure_connected()
        params = list(params) if params is not None else []

        logger.info("Ejecutando fetch_one: %s | params=%s", query, params)

        cursor = await conn.cursor()
        try:
            await cursor.execute(query, params)
            row = await cursor.fetchone()
            if row is None:
                logger.info("fetch_one: sin resultados")
                return None

            columns = [col[0] for col in cursor.description]
            result = {col: value for col, value in zip(columns, row)}

            logger.info("fetch_one: fila encontrada")
            return result

        except Exception:
            logger.exception("Error ejecutando fetch_one: %s", query)
            raise
        finally:
            await cursor.close()

    # -------------------------------------------------------------------------
    # Operaciones de modificación (INSERT, UPDATE, DELETE)
    # -------------------------------------------------------------------------
    async def execute_non_query(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> int:
        """
        Ejecuta una operación de modificación (INSERT, UPDATE, DELETE).

        Si la conexión está en modo autocommit=True, la operación se confirma
        automáticamente. Si se encuentra dentro de una transacción iniciada
        con `begin_transaction`, la confirmación dependerá de `commit()`.

        Args:
            query: Sentencia SQL con placeholders `?`.
            params: Secuencia de parámetros posicionales.

        Returns:
            Número de filas afectadas (si el driver lo reporta).
        """
        conn = self._ensure_connected()
        params = list(params) if params is not None else []

        logger.info("Ejecutando non-query: %s | params=%s", query, params)

        cursor = await conn.cursor()
        try:
            await cursor.execute(query, params)

            # Si no está en transacción y autocommit está desactivado,
            # se realiza un commit explícito (caso raro, pero seguro).
            if not self._in_transaction and not conn.autocommit:
                logger.debug("Autocommit=False y fuera de transacción: commit implícito")
                await conn.commit()

            rowcount = cursor.rowcount
            logger.info("non-query completado: %d filas afectadas", rowcount)
            return rowcount

        except Exception:
            logger.exception("Error ejecutando non-query: %s", query)
            # Si no está en una transacción gestionada explícitamente,
            # se puede intentar rollback por seguridad.
            if not self._in_transaction and not conn.autocommit:
                try:
                    await conn.rollback()
                    logger.info("Rollback automático aplicado por error en non-query")
                except Exception:
                    logger.exception("Error al hacer rollback automático")
            raise
        finally:
            await cursor.close()

    # -------------------------------------------------------------------------
    # Manejo explícito de transacciones
    # -------------------------------------------------------------------------
    async def begin_transaction(self) -> None:
        """
        Inicia una transacción explícita desactivando autocommit.
        """
        conn = self._ensure_connected()

        if self._in_transaction:
            raise RuntimeError("Ya existe una transacción activa")

        logger.info("BEGIN TRANSACTION")
        try:
            conn.autocommit = False
            self._in_transaction = True
        except Exception:
            logger.exception("Error al iniciar la transacción")
            raise

    async def commit(self) -> None:
        """
        Confirma la transacción actual y restaura el estado de autocommit.
        """
        conn = self._ensure_connected()

        if not self._in_transaction:
            logger.warning("commit() llamado sin transacción activa")
            return

        logger.info("COMMIT")
        try:
            await conn.commit()
        except Exception:
            logger.exception("Error durante COMMIT")
            raise
        finally:
            conn.autocommit = self._autocommit_default
            self._in_transaction = False

    async def rollback(self) -> None:
        """
        Revierte la transacción actual y restaura el estado de autocommit.
        """
        conn = self._ensure_connected()

        if not self._in_transaction:
            logger.warning("rollback() llamado sin transacción activa")
            return

        logger.info("ROLLBACK")
        try:
            await conn.rollback()
        except Exception:
            logger.exception("Error durante ROLLBACK")
            raise
        finally:
            conn.autocommit = self._autocommit_default
            self._in_transaction = False

    # -------------------------------------------------------------------------
    # Context manager de transacción
    # -------------------------------------------------------------------------
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["SQLServerClientAsync"]:
        """
        Context manager asíncrono para gestionar una transacción.

        Uso:
            async with client.transaction():
                await client.execute_non_query(...)
                await client.execute_non_query(...)

        - Hace BEGIN al entrar.
        - Hace COMMIT si no hay excepción.
        - Hace ROLLBACK si ocurre alguna excepción.
        """
        await self.begin_transaction()
        try:
            yield self
        except Exception:
            # Si algo falla, se intenta rollback y se debe volver a lanzar.
            try:
                await self.rollback()
            except Exception:
                logger.exception("Error al hacer rollback dentro del context manager")
            raise
        else:
            await self.commit()

