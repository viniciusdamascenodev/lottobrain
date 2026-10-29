"""Cache apenas de teste: clone SQL de aprovação REAL, restrito ao mesmo cluster.

Não exporta certificados nem credenciais; o runner completo continua falhando
se o cenário que publicou o template falhar posteriormente.
"""
import os
from uuid import uuid4
import psycopg
from psycopg import sql

_fixture=None


def publish_approved_fixture(case,checkpoint):
    global _fixture
    name="lottobrain_test_approved_"+uuid4().hex
    with psycopg.connect(os.environ["LOTTOBRAIN_TEST_ADMIN_DSN"],autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {} OWNER lb_migrator").format(
            sql.Identifier(name),sql.Identifier(case.database)))
    _fixture={"cluster":os.environ["LOTTOBRAIN_TEST_ISOLATED"],"template":name,
              "catalog":case.catalog,"checkpoint":checkpoint}


def approved_fixture():
    if _fixture and _fixture["cluster"]==os.environ.get("LOTTOBRAIN_TEST_ISOLATED"):
        return _fixture
    return None
