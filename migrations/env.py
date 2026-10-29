"""DDL explícito; domínio e coletores não dependem do Alembic."""
import os

from alembic import context
from sqlalchemy import create_engine, pool


def migrate(connection):
    if connection.in_transaction():
        raise RuntimeError("Forneça uma conexão dedicada, sem transação ativa, para migrations.")
    if connection.dialect.name != "postgresql":
        raise RuntimeError("As migrations exigem PostgreSQL 17.")
    version = connection.exec_driver_sql("SHOW server_version_num").scalar_one()
    if not 170000 <= int(version) < 180000:
        raise RuntimeError("Versão qualificada: PostgreSQL 17.x.")
    connection.commit()
    # Lote de DDL + ledger em uma transação: lock vale até o último passo,
    # e downgrade recusado não deixa versões vazias parcialmente revertidas.
    context.configure(connection=connection, target_metadata=None, transaction_per_migration=False)
    with context.begin_transaction():
        # Serializa migradores, sem manter lock durante operações externas.
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(240024)")
        context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Use um banco PostgreSQL dedicado; SQL offline não comprova integridade.")
else:
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        migrate(supplied)
    else:
        url = os.environ.get("LOTTOBRAIN_DATABASE_URL")
        if not url:
            raise RuntimeError("Defina LOTTOBRAIN_DATABASE_URL (postgresql+psycopg://...).")
        engine = create_engine(url, poolclass=pool.NullPool, hide_parameters=True, connect_args={"connect_timeout":10})
        try:
            with engine.connect() as connection:
                migrate(connection)
        finally:
            engine.dispose()
