"""Uma conexão por unidade; nunca entrega SQL/DSN em erros de aplicação."""
import psycopg
from psycopg.rows import dict_row

from app.application.persistence import PersistenceError
from app.infrastructure.postgres.captures import PgCaptureRepository
from app.infrastructure.postgres.catalog import PgCatalogRepository
from app.infrastructure.postgres.common import translate
from app.infrastructure.postgres.draws import PgDrawRepository
from app.infrastructure.postgres.processing import PgProcessingRepository
from app.infrastructure.postgres.sync import PgSyncRepository
from app.infrastructure.postgres.historical_pilot import PgHistoricalPilotRepository
from app.infrastructure.postgres.historical_import import PgHistoricalImportRepository
from app.infrastructure.postgres.baselines import PgBaselineRepository
from app.infrastructure.postgres.sync_batches import PgSyncBatchRepository


class PgUnitOfWork:
    def __init__(self, connect, observe=lambda stage, db: None):
        self.connect = connect
        self.observe = observe
        self.connection = None

    def __enter__(self):
        try:
            self.connection = db = self.connect()
            db.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            db.execute("SET LOCAL lock_timeout='10s'")
            db.execute("SET LOCAL statement_timeout='20s'")
            self.catalog = PgCatalogRepository(db)
            self.captures = PgCaptureRepository(db)
            self.processing = PgProcessingRepository(db)
            self.draws = PgDrawRepository(db,self.checkpoint)
            self.sync = PgSyncRepository(db,self.checkpoint)
            self.pilot = PgHistoricalPilotRepository(db,self.checkpoint)
            self.history = PgHistoricalImportRepository(db,self.checkpoint)
            self.baselines = PgBaselineRepository(db,self.checkpoint)
            self.batches = PgSyncBatchRepository(db,self.checkpoint)
            return self
        except Exception as error:
            if self.connection is not None:
                self.connection.close()
            if isinstance(error,psycopg.Error):
                raise translate(error) from None
            raise

    def checkpoint(self, stage):
        self.observe(stage,self.connection)

    def _rollback(self):
        try:
            self.connection.rollback()
        except Exception:
            pass  # Preservar erro original; finally ainda fecha a conexão.

    def __exit__(self, exc_type, exc, traceback):
        committed = False
        commit_started = False
        try:
            if exc is not None:
                self._rollback()
                if isinstance(exc,psycopg.Error):
                    raise translate(exc) from None
                return False
            self.checkpoint("before_commit")
            commit_started = True
            self.connection.commit()
            committed = True
            self.checkpoint("after_commit")
        except psycopg.Error as error:
            if not committed:
                self._rollback()
            if committed or error.sqlstate is None or (error.sqlstate or "").startswith("08"):
                raise PersistenceError("commit_outcome_unknown") from None
            raise translate(error) from None
        except OSError:
            if not committed:
                self._rollback()
            raise PersistenceError("commit_outcome_unknown" if commit_started else "database_unavailable") from None
        finally:
            self.connection.close()


class PgUnitOfWorkFactory:
    def __init__(self, *, connect=None, dsn=None, observe=lambda stage, db: None):
        if connect is None and dsn is None:
            raise ValueError("Conexão PostgreSQL explícita necessária")
        self.connect = connect or (lambda: psycopg.connect(dsn, row_factory=dict_row, connect_timeout=10,
                                                         application_name="lottobrain-pg-ingestion"))
        self.observe = observe

    def __call__(self):
        return PgUnitOfWork(self.connect,self.observe)
