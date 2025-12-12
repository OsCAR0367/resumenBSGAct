import httpx
from typing import Optional, Union, Any, Dict, List
from urllib.parse import urljoin


class ApiClientAsync:
    """Cliente asíncrono para realizar peticiones HTTP a APIs REST."""

    def __init__(
            self,
            base_url: str,
            verify_ssl: bool = True,
            timeout: int = 20,
            default_headers: Optional[Dict[str, str]] = None
    ):
        """
        Inicializa el cliente API.

        :param base_url: URL base del API
        :param verify_ssl: Si se debe verificar certificados SSL
        :param timeout: Timeout en segundos para las peticiones
        :param default_headers: Headers que se incluirán en todas las peticiones
        """
        self.base_url = base_url.rstrip("/")
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.default_headers = default_headers or {}
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager para manejo automático de cliente"""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers=self.default_headers,
             follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cierra el cliente automáticamente"""
        if self.client:
            await self.client.aclose()

    def _build_url(self, endpoint: str, resource_paths: Optional[List[Union[str, int]]] = None) -> str:
        """
        Construye la URL final para la solicitud.

        :param endpoint: Endpoint base
        :param resource_paths: Lista de segmentos adicionales del path
        :return: URL completa
        """
        endpoint = endpoint.lstrip("/")

        if resource_paths:
            # Filtrar valores None y convertir a string
            valid_paths = [str(p) for p in resource_paths if p is not None]
            if valid_paths:
                endpoint = f"{endpoint}/{'/'.join(valid_paths)}"

        return urljoin(f"{self.base_url}/", endpoint)

    async def _create_temporary_client(self) -> httpx.AsyncClient:
        """
        Crea un AsyncClient con connection pooling.
        """
        return httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.verify_ssl,
            headers=self.default_headers,
            follow_redirects=True,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100
            )
        )

    async def create_client(self):
        self.client = await self._create_temporary_client()

    async def request_async(
            self,
            endpoint: str,
            resource_paths: Optional[List[Union[str, int]]] = None,
            method: str = "GET",
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            stream: bool = False,
            **kwargs
    ) -> Any:
        """
        Realiza una solicitud HTTP genérica de forma asíncrona.

        Las excepciones NO se manejan internamente, se propagan al llamador.

        :param endpoint: Ruta del endpoint (ej. 'usuarios')
        :param resource_paths: Lista de segmentos adicionales en el path (ej. [123, 'detalles'])
        :param method: Método HTTP (GET, POST, PUT, DELETE, PATCH)
        :param headers: Diccionario de encabezados (se combinan con default_headers)
        :param params: Diccionario con parámetros querystring
        :param json_data: Diccionario con datos JSON (para POST/PUT/PATCH)
        :param stream: Si True, retorna un objeto Response para streaming (no cierra automáticamente)
        :param kwargs: Parámetros adicionales que se pasan a httpx
        :return: Datos de la respuesta (JSON parseado o texto), o Response si stream=True
        :raises httpx.HTTPStatusError: Si el servidor responde con un código de error HTTP
        :raises httpx.TimeoutException: Si la petición excede el timeout configurado
        :raises httpx.RequestError: Si hay un error en la conexión o petición
        """
        url = self._build_url(endpoint, resource_paths)
        method = method.upper()

        # Combinar headers default con los específicos de esta petición
        final_headers = {**self.default_headers, **(headers or {})}

        # Usar cliente existente o crear uno temporal
        use_temporary_client = self.client is None
        if use_temporary_client:
            client = await self._create_temporary_client()
        else:
            client = self.client

        try:
            # Si stream=True, se debe mantener el cliente abierto
            if stream:
                response = client.stream(
                    method=method,
                    url=url,
                    headers=final_headers,
                    params=params,
                    json=json_data,
                    **kwargs
                )
                # Para streaming, retornar el context manager del response
                # El usuario debe manejarlo con 'async with'
                return response

            # Comportamiento normal (no-streaming)
            response = await client.request(
                method=method,
                url=url,
                headers=final_headers,
                params=params,
                json=json_data,
                **kwargs
            )

            # Verificar status code (lanza HTTPStatusError si hay error)
            response.raise_for_status()

            # Parsear como JSON, si falla lanza JSONDecodeError
            return response.json()

        finally:
            # Solo cerrar cliente temporal si NO es streaming
            if use_temporary_client and not stream:
                await client.aclose()

    # Métodos de conveniencia async para diferentes verbos HTTP
    async def get_async(
            self,
            endpoint: str,
            resource_paths: Optional[List[Union[str, int]]] = None,
            stream: bool = False,
            params: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Any:
        """Realiza una solicitud GET asíncrona"""
        return await self.request_async(endpoint, resource_paths, method="GET", stream=stream, params=params, **kwargs)

    async def post_async(
            self,
            endpoint: str,
            resource_paths: Optional[List[Union[str, int]]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Any:
        """Realiza una solicitud POST asíncrona"""
        return await self.request_async(endpoint, resource_paths, method="POST", json_data=json_data, **kwargs)

    async def put_async(
            self,
            endpoint: str,
            resource_paths: Optional[List[Union[str, int]]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Any:
        """Realiza una solicitud PUT asíncrona"""
        return await self.request_async(endpoint, resource_paths, method="PUT", json_data=json_data, **kwargs)

    async def delete_async(
            self,
            endpoint: str,
            resource_paths: Optional[List[Union[str, int]]] = None,
            **kwargs
    ) -> Any:
        """Realiza una solicitud DELETE asíncrona"""
        return await self.request_async(endpoint, resource_paths, method="DELETE", **kwargs)

    async def patch_async(
            self,
            endpoint: str,
            resource_paths: Optional[List[Union[str, int]]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            **kwargs
    ) -> Any:
        """Realiza una solicitud PATCH asíncrona"""
        return await self.request_async(endpoint, resource_paths, method="PATCH", json_data=json_data, **kwargs)
