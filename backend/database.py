from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    from backend.models import (  # noqa: F401
        Analysis,
        AnalysisStep,
        AnalysisReport,
        BacktestResult,
        SkillVersion,
    )

    Base.metadata.create_all(bind=engine)

    # Migrate: add commit_sha column if not present
    with engine.connect() as conn:
        from sqlalchemy import inspect, text

        inspector = inspect(conn)
        for table_name, col_name in [
            ("skill_versions", "commit_sha"),
            ("analyses", "analysis_date"),
        ]:
            columns = [c["name"] for c in inspector.get_columns(table_name)]
            if col_name not in columns:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} VARCHAR"))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
