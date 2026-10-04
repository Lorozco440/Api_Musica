"""Administrative operations available only through local terminal access."""
import argparse
from getpass import getpass
from sqlalchemy import select
from .database import Base, engine, SessionLocal
from .models import User, Artist, Album, Song
from .schemas import Register
from .security import password_hasher
from .services import save


def main():
    parser = argparse.ArgumentParser(description="Administración local de MusicAPI")
    parser.add_argument("command", choices=["init-db", "create-admin", "seed"])
    args = parser.parse_args()
    if args.command == "init-db":
        Base.metadata.create_all(engine)
        print("Tablas creadas. Este comando no migra tablas existentes.")
        return
    with SessionLocal() as db:
        if args.command == "create-admin":
            email = input("Correo del administrador: ").strip()
            name = input("Nombre: ").strip()
            password = getpass("Contraseña (mínimo 12 caracteres): ")
            if password != getpass("Repita la contraseña: "):
                raise SystemExit("Las contraseñas no coinciden.")
            try:
                data = Register(name=name, email=email, password=password)
            except ValueError:
                raise SystemExit("Datos inválidos: revise correo, nombre y longitud de contraseña.") from None
            if db.scalar(select(User).where(User.email == str(data.email).lower())):
                raise SystemExit("Ya existe un usuario con ese correo; no se modificó su rol.")
            save(db, User(name=data.name, email=str(data.email).lower(),
                          password_hash=password_hasher.hash(data.password), role="admin"))
            print("Administrador creado.")
        else:
            if db.scalar(select(Artist.id).limit(1)):
                print("El catálogo ya tiene datos; no se agregó contenido.")
                return
            artist = Artist(name="Aurora del Lago")
            db.add(artist)
            db.flush()
            album = Album(title="Horizontes", artist_id=artist.id)
            db.add(album)
            db.flush()
            db.add_all([Song(title=title, album_id=album.id, duration_seconds=duration)
                        for title, duration in [("Amanecer", 210), ("Brisa", 185), ("Camino a casa", 240)]])
            db.commit()
            print("Catálogo ficticio creado: 1 artista, 1 álbum y 3 canciones.")


if __name__ == "__main__":
    main()
