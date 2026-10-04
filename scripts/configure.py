"""Generate a local secret once; never print it or overwrite existing configuration."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / '.env'
try:
    with path.open('x') as file:
        file.write(f'JWT_SECRET={secrets.token_urlsafe(48)}\nDATABASE_URL=sqlite:///./music.db\n')
    path.chmod(0o600)
    print('Archivo .env creado con una clave aleatoria. No lo comparta.')
except FileExistsError:
    print('El archivo .env ya existe; se conserva su configuración.')
