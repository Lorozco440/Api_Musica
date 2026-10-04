# Propuesta de buenas prácticas para el desarrollo de MusicAPI

## Introducción

MusicAPI es una API REST inspirada en una plataforma musical como Spotify. Permite registrar clientes, consultar artistas, álbumes y canciones, y administrar listas de reproducción privadas. Utiliza Python, FastAPI, SQLAlchemy y SQLite, con autenticación mediante JSON Web Tokens (JWT).

Esta propuesta establece buenas prácticas para mantener el código organizado, proteger los datos y facilitar la evolución de la aplicación.

## 1. Organización del código

Se propone separar la aplicación por responsabilidades:

- **Rutas:** reciben solicitudes y devuelven respuestas.
- **Esquemas:** validan los datos de entrada y definen las respuestas.
- **Modelos:** representan las tablas de la base de datos.
- **Servicios:** concentran operaciones compartidas y reglas del negocio.
- **Seguridad:** administra contraseñas, tokens y permisos.

Esta separación facilita localizar errores, realizar cambios y reutilizar código.

## 2. Autenticación y protección de contraseñas

Las contraseñas se almacenan mediante **hash con Argon2id**, nunca en texto plano. Durante el inicio de sesión, la aplicación verifica la contraseña contra el hash almacenado.

Después de validar las credenciales, la API emite un JWT con vencimiento. Cada solicitud protegida debe enviarlo en el encabezado:

```http
Authorization: Bearer <token>
```

El servidor valida la firma, el algoritmo permitido, el vencimiento, el emisor y la audiencia. Los tokens no deben contener contraseñas ni información sensible, ya que su firma no cifra el contenido.

## 3. Autorización y control de acceso

La autenticación identifica al usuario; la autorización determina qué operaciones puede realizar.

MusicAPI diferencia dos roles:

- **Cliente:** consulta el catálogo y administra sus propias playlists.
- **Administrador:** también puede crear, modificar y eliminar contenido del catálogo.

Las operaciones sobre playlists comprueban su propietario, incluso cuando quien solicita acceso es administrador. Además, el registro público siempre crea clientes y rechaza campos adicionales que permitan intentar asignarse privilegios.

## 4. Validación de datos

Se propone validar los datos antes de procesarlos o almacenarlos. La aplicación comprueba correos electrónicos, campos obligatorios, longitudes, identificadores positivos y duración válida de canciones.

También se definen explícitamente los campos que pueden modificarse. Esto evita entradas inconsistentes y cambios no autorizados en atributos como el rol del usuario.

## 5. Integridad de la base de datos

Se utilizan claves primarias, claves foráneas y restricciones de unicidad para mantener relaciones consistentes.

Por ejemplo:

- Un correo electrónico no puede registrarse dos veces.
- Una canción debe pertenecer a un álbum existente.
- Una canción no puede repetirse dentro de la misma playlist.
- Un álbum con canciones no puede eliminarse sin resolver primero esas relaciones.

Las operaciones de escritura utilizan transacciones. SQLAlchemy permite construir consultas parametrizadas, evitando concatenar entradas del usuario dentro de instrucciones SQL.

## 6. Diseño de endpoints y manejo de errores

Los endpoints se organizan por recursos y utilizan el prefijo `/api/v1` para identificar la versión.

Se emplean métodos HTTP según la operación: `GET` para consultar, `POST` para crear, `PATCH` para actualizar parcialmente, `PUT` para reemplazar y `DELETE` para eliminar.

Las respuestas utilizan códigos coherentes:

| Código | Significado |
|---|---|
| 200 | Operación exitosa |
| 201 | Recurso creado |
| 204 | Eliminación exitosa, sin contenido |
| 401 | Autenticación ausente o inválida |
| 403 | Permisos insuficientes |
| 404 | Recurso no encontrado o playlist ajena |
| 409 | Conflicto de datos o relaciones |
| 422 | Datos de entrada inválidos |
| 429 | Límite de solicitudes excedido |

Los errores mantienen una estructura uniforme y no muestran contraseñas, consultas SQL ni detalles internos del servidor.

## 7. Protección de recursos y configuración

Las consultas de listas utilizan paginación, con un máximo de 100 resultados por solicitud. El registro y el inicio de sesión comparten un límite local de solicitudes por IP para reducir intentos automatizados.

Las claves de firma y credenciales se mantienen fuera del código mediante variables de entorno. El archivo `.env`, las bases de datos locales y el entorno virtual deben excluirse del repositorio con `.gitignore`. Se puede conservar `.env.example` como referencia, sin secretos reales.

## 8. Documentación y pruebas

La documentación OpenAPI y la interfaz Swagger permiten conocer los endpoints, sus parámetros y sus respuestas.

Las pruebas automatizadas verifican tanto operaciones exitosas como situaciones de rechazo: credenciales incorrectas, tokens inválidos o vencidos, intentos de asignarse privilegios, acceso a playlists ajenas y conflictos de integridad.

Estas comprobaciones ayudan a detectar regresiones cuando se modifica el proyecto.

## 9. Mejoras propuestas para producción

La implementación actual tiene un alcance académico. Antes de publicarla para usuarios reales, se propone:

- Implementar HTTPS para proteger las comunicaciones.
- Incorporar migraciones con Alembic para controlar cambios del esquema.
- Evaluar PostgreSQL para mayores necesidades de concurrencia.
- Sustituir el limitador en memoria por un mecanismo compartido entre procesos.
- Definir renovación y revocación de sesiones.
- Incorporar monitoreo, registros sin datos sensibles y copias de seguridad verificadas.
- Automatizar la ejecución de pruebas antes de integrar cambios.

Actualmente, la creación de tablas no realiza migraciones, el límite de solicitudes funciona por proceso y los tokens permanecen válidos hasta su vencimiento. Estas limitaciones deben considerarse al ampliar el sistema.

## Exposición de la propuesta

La demostración presentará el registro de un cliente, el inicio de sesión, la autorización con JWT, la consulta del catálogo y la creación de una playlist con canciones.

Después se mostrarán dos operaciones rechazadas: administrar el catálogo con una cuenta de cliente y acceder a una playlist perteneciente a otro usuario. Esto permitirá comprobar que la API distingue entre identidad, rol y propiedad de los recursos.

La propuesta busca que MusicAPI sea comprensible, verificable y fácil de mantener, con controles de seguridad acordes con su alcance y una ruta definida para su evolución.

## Referencias

- [FastAPI: autenticación con JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [OWASP: seguridad de servicios REST](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html)
- [OWASP: almacenamiento de contraseñas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [SQLAlchemy: claves foráneas en SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support)
