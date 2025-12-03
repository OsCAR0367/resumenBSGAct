from app.infrastructure.database.connection_sqlserver import SessionLocal


def get_db():
    """
    Dependencia para obtener sesión de base de datos
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()