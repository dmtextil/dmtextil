import os
import json
from datetime import datetime
from decimal import Decimal

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Cliente,
    Maquina,
    Artigo,
    Producao,
    BaixaLote,
    FaturamentoExtra,
    Usuario
)


def serializar_valor(valor):
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def serializar_registro(obj):
    item = obj.__dict__.copy()
    item.pop("_sa_instance_state", None)

    for chave, valor in item.items():
        item[chave] = serializar_valor(valor)

    return item


def main():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL não encontrada.")

    b2_bucket_name = os.getenv("B2_BUCKET_NAME")
    b2_endpoint_url = os.getenv("B2_ENDPOINT_URL")
    b2_key_id = os.getenv("B2_KEY_ID")
    b2_application_key = os.getenv("B2_APPLICATION_KEY")

    if not all([b2_bucket_name, b2_endpoint_url, b2_key_id, b2_application_key]):
        raise ValueError("Variáveis do Backblaze B2 não configuradas corretamente.")

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        tabelas = [
            Cliente,
            Maquina,
            Artigo,
            Producao,
            BaixaLote,
            FaturamentoExtra,
            Usuario
        ]

        dados = {}

        for tabela in tabelas:
            registros = db.query(tabela).all()
            dados[tabela.__tablename__] = [serializar_registro(r) for r in registros]

        conteudo = json.dumps(dados, indent=2, ensure_ascii=False)

        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        nome_arquivo = f"backup_malharia_{timestamp}.json"

        s3 = boto3.client(
            "s3",
            endpoint_url=b2_endpoint_url,
            aws_access_key_id=b2_key_id,
            aws_secret_access_key=b2_application_key
        )

        s3.put_object(
            Bucket=b2_bucket_name,
            Key=nome_arquivo,
            Body=conteudo.encode("utf-8"),
            ContentType="application/json"
        )

        print(f"Backup enviado com sucesso: {nome_arquivo}")

    finally:
        db.close()


if __name__ == "__main__":
    main()