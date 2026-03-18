from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from app.database import Base


class Artigo(Base):
    __tablename__ = "artigos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False)
    codigo = Column(String(50), unique=True)
    valor_kg = Column(Numeric(10,2), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    ativo = Column(Boolean, default=True)
    cliente = relationship("Cliente")


class Maquina(Base):
    __tablename__ = "maquinas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(50), unique=True)
    ativa = Column(Boolean, default=True)


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(120), nullable=False, unique=True)
    ativo = Column(Boolean, default=True)

class Producao(Base):
    __tablename__ = "producoes"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(String(20), nullable=False)
    turno = Column(String(20), nullable=False)
    lote = Column(String(2), nullable=False)
    pecas = Column(Integer, nullable=False)
    saldo_pecas = Column(Integer, nullable=False)
    saldo_peso = Column(Numeric(10, 2), nullable=False)
    maquina_id = Column(Integer, ForeignKey("maquinas.id"), nullable=False)
    artigo_id = Column(Integer, ForeignKey("artigos.id"), nullable=False)
    peso = Column(Numeric(10, 2), nullable=False)
    valor_kg = Column(Numeric(10, 2), nullable=False)
    valor_total = Column(Numeric(10, 2), nullable=False)

    maquina = relationship("Maquina")
    artigo = relationship("Artigo")

class BaixaLote(Base):
    __tablename__ = "baixas_lotes"

    id = Column(Integer, primary_key=True, index=True)
    romaneio_id = Column(Integer)
    data = Column(String(20), nullable=False)
    producao_id = Column(Integer, ForeignKey("producoes.id"))
    maquina_id = Column(Integer, ForeignKey("maquinas.id"))
    artigo_id = Column(Integer, ForeignKey("artigos.id"))
    lote = Column(String(2), nullable=False)
    pecas = Column(Integer, nullable=False)
    peso = Column(Numeric(10, 2), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    fechado = Column(Boolean, default=False)

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, nullable=False)

    senha_hash = Column(String(255), nullable=False)

    ativo = Column(Boolean, default=True)

class FaturamentoExtra(Base):
    __tablename__ = "faturamentos_extras"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(String(20), nullable=False)
    descricao = Column(String(200), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)