from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext
from app import models

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")



def criar_artigo(db: Session, nome: str, codigo: str, valor_kg: float, cliente_id: int):
    novo_artigo = models.Artigo(
        nome=nome,
        codigo=codigo,
        valor_kg=valor_kg,
        cliente_id=cliente_id
    )

    db.add(novo_artigo)
    db.commit()
    db.refresh(novo_artigo)

    return novo_artigo


def listar_artigos(db: Session):
    return db.query(models.Artigo).options(
        joinedload(models.Artigo.cliente)
    ).all()


def criar_cliente(db: Session, nome: str):
    novo_cliente = models.Cliente(nome=nome)

    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)

    return novo_cliente


def listar_clientes(db: Session):
    return db.query(models.Cliente).all()


def criar_maquina(db: Session, nome: str):
    nova_maquina = models.Maquina(nome=nome)

    db.add(nova_maquina)
    db.commit()
    db.refresh(nova_maquina)

    return nova_maquina


def listar_maquinas(db: Session):
    return db.query(models.Maquina).all()

def criar_producao(db: Session, data: str, turno: str, maquina_id: int, artigo_id: int, lote: str, pecas: int, peso: float):

    artigo = db.query(models.Artigo).filter(models.Artigo.id == artigo_id).first()

    valor_kg = float(artigo.valor_kg)
    valor_total = float(peso) * valor_kg

    nova_producao = models.Producao(
        data=data,
        turno=turno,
        maquina_id=maquina_id,
        artigo_id=artigo_id,
        lote=lote,
        pecas=pecas,
        saldo_pecas=pecas,
        peso=peso,
        saldo_peso=peso,
        valor_kg=valor_kg,
        valor_total=valor_total
    )

    db.add(nova_producao)
    db.commit()
    db.refresh(nova_producao)

    return nova_producao


def listar_producoes(db: Session):
    return db.query(models.Producao).options(
        joinedload(models.Producao.maquina),
        joinedload(models.Producao.artigo).joinedload(models.Artigo.cliente)
    ).filter(
        models.Producao.saldo_pecas > 0
    ).order_by(
        models.Producao.maquina_id,
        models.Producao.lote
    ).all()

def total_por_turno(db: Session, data: str, turno: str):
    producoes = db.query(models.Producao).filter(
        models.Producao.data == data,
        models.Producao.turno == turno
    ).all()

    return sum(float(producao.peso) for producao in producoes)


def total_do_dia(db: Session, data: str):
    producoes = db.query(models.Producao).filter(
        models.Producao.data == data
    ).all()

    return sum(float(producao.peso) for producao in producoes)


def valor_total_do_dia(db: Session, data: str):
    producoes = db.query(models.Producao).filter(
        models.Producao.data == data
    ).all()

    return sum(float(producao.valor_total) for producao in producoes)


def resumo_por_maquina_no_dia(db: Session, data: str):
    producoes = db.query(models.Producao).filter(
        models.Producao.data == data
    ).all()

    resumo = {}

    for producao in producoes:
        nome_maquina = producao.maquina.nome

        if nome_maquina not in resumo:
            resumo[nome_maquina] = {
                "peso_total": 0,
                "valor_total": 0
            }

        resumo[nome_maquina]["peso_total"] += float(producao.peso)
        resumo[nome_maquina]["valor_total"] += float(producao.valor_total)

    return resumo

def baixar_lote(db: Session, producao_id: int, pecas_baixadas: int):

    producao = db.query(models.Producao).filter(
        models.Producao.id == producao_id
    ).first()

    if not producao:
        return

    if pecas_baixadas > producao.saldo_pecas or pecas_baixadas <= 0:
        return

    peso_medio = float(producao.peso) / float(producao.pecas)
    peso_baixado = peso_medio * pecas_baixadas
    valor_baixado = peso_baixado * float(producao.valor_kg)

    # reduzir saldo do lote
    producao.saldo_pecas -= pecas_baixadas
    producao.saldo_peso = float(producao.saldo_peso) - float(peso_baixado)

    # procurar a última baixa ABERTA da mesma máquina
    ultima_baixa_aberta = db.query(models.BaixaLote).filter(
        models.BaixaLote.maquina_id == producao.maquina_id,
        models.BaixaLote.fechado == False
    ).order_by(
        models.BaixaLote.id.desc()
    ).first()

    if ultima_baixa_aberta and ultima_baixa_aberta.romaneio_id:
        romaneio_id = ultima_baixa_aberta.romaneio_id
    else:
        ultima_baixa = db.query(models.BaixaLote).order_by(
            models.BaixaLote.id.desc()
        ).first()

        if ultima_baixa and ultima_baixa.romaneio_id:
            romaneio_id = ultima_baixa.romaneio_id + 1
        else:
            romaneio_id = 1

    nova_baixa = models.BaixaLote(
        data=producao.data,
        producao_id=producao.id,
        maquina_id=producao.maquina_id,
        artigo_id=producao.artigo_id,
        lote=producao.lote,
        pecas=pecas_baixadas,
        peso=peso_baixado,
        valor=valor_baixado,
        romaneio_id=romaneio_id,
        fechado=False
    )

    db.add(nova_baixa)
    db.commit()


def resumo_estoque(db: Session):

    producoes = db.query(models.Producao).filter(
        models.Producao.saldo_pecas > 0
    ).all()

    total_pecas = sum(p.saldo_pecas for p in producoes)
    total_peso = sum(float(p.saldo_peso) for p in producoes)

    return total_pecas, total_peso


def estoque_por_artigo(db: Session):

    producoes = db.query(models.Producao).filter(
        models.Producao.saldo_pecas > 0
    ).all()

    resumo = {}

    for p in producoes:

        nome_artigo = p.artigo.nome

        if nome_artigo not in resumo:
            resumo[nome_artigo] = {
                "pecas": 0,
                "peso": 0
            }

        resumo[nome_artigo]["pecas"] += p.saldo_pecas
        resumo[nome_artigo]["peso"] += float(p.saldo_peso)

    return resumo

def gerar_romaneio(db: Session):

    ultima_baixa = db.query(models.BaixaLote).order_by(
        models.BaixaLote.id.desc()
    ).first()

    if not ultima_baixa:
        return None

    romaneio_id = ultima_baixa.romaneio_id

    baixas = db.query(models.BaixaLote).filter(
        models.BaixaLote.romaneio_id == romaneio_id
    ).all()

    if not baixas:
        return None

    maquina = db.query(models.Maquina).filter(
        models.Maquina.id == baixas[0].maquina_id
    ).first()

    artigo = db.query(models.Artigo).filter(
        models.Artigo.id == baixas[0].artigo_id
    ).first()

    lotes = sorted(set(b.lote for b in baixas))

    total_pecas = sum(b.pecas for b in baixas)
    total_peso = sum(float(b.peso) for b in baixas)
    valor_total = sum(float(b.valor) for b in baixas)

    # data do romaneio = data da última baixa
    data_romaneio = baixas[-1].data

    # converter data para formato brasileiro
    data_br = data_romaneio
    if data_romaneio and "-" in data_romaneio:
        partes = data_romaneio.split("-")
        if len(partes) == 3:
            data_br = f"{partes[2]}/{partes[1]}/{partes[0]}"

    return {
        "romaneio_id": romaneio_id,
        "data": data_br,
        "maquina": maquina.nome if maquina else "",
        "artigo": artigo.nome if artigo else "",
        "lotes": ", ".join(lotes),
        "total_pecas": total_pecas,
        "total_peso": total_peso,
        "valor_total": valor_total
    }

def estoque_por_cliente(db: Session):

    producoes = db.query(models.Producao).filter(
        models.Producao.saldo_pecas > 0
    ).all()

    resumo = {}

    for p in producoes:

        nome_cliente = p.artigo.cliente.nome

        if nome_cliente not in resumo:
            resumo[nome_cliente] = {
                "pecas": 0,
                "peso": 0,
                "valor": 0
            }

        resumo[nome_cliente]["pecas"] += p.saldo_pecas
        resumo[nome_cliente]["peso"] += float(p.saldo_peso)
        resumo[nome_cliente]["valor"] += float(p.saldo_peso) * float(p.valor_kg)

    return resumo

def ajustar_saldo_lote(db: Session, producao_id: int, novo_saldo: int):

    producao = db.query(models.Producao).filter(
        models.Producao.id == producao_id
    ).first()

    if not producao:
        return

    if novo_saldo < 0:
        return

    # peso médio por peça
    if producao.pecas > 0:
        peso_medio = float(producao.peso) / float(producao.pecas)
    else:
        peso_medio = 0

    producao.saldo_pecas = novo_saldo
    producao.saldo_peso = peso_medio * novo_saldo

    db.commit()

def concluir_romaneio(db: Session):

    # pegar a última baixa registrada
    ultima_baixa = db.query(models.BaixaLote).order_by(
        models.BaixaLote.id.desc()
    ).first()

    if not ultima_baixa:
        return

    romaneio_id = ultima_baixa.romaneio_id

    # marcar todas as baixas desse romaneio como fechadas
    db.query(models.BaixaLote).filter(
        models.BaixaLote.romaneio_id == romaneio_id
    ).update({"fechado": True})

    db.commit()

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER


def gerar_pdf_romaneio(dados, caminho_arquivo):
    doc = SimpleDocTemplate(
        caminho_arquivo,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elementos = []

    titulo_style = ParagraphStyle(
        name="TituloCentral",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        spaceAfter=6
    )

    subtitulo_style = ParagraphStyle(
        name="SubtituloCentral",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=12
    )

    elementos.append(Paragraph("ROMANEIO", titulo_style))
    elementos.append(Paragraph("Sistema de Produção da Malharia", subtitulo_style))

    tabela_meta = Table([
        ["Nº do Romaneio", str(dados["romaneio_id"])],
        ["Data", dados["data"]],
    ], colWidths=[150, 330])

    tabela_meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(tabela_meta)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Informações Gerais", styles["Heading3"]))

    tabela_info = Table([
        ["Máquina", dados["maquina"]],
        ["Artigo", dados["artigo"]],
    ], colWidths=[150, 330])

    tabela_info.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela_info)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Lotes do Romaneio", styles["Heading3"]))

    tabela_lotes = Table([
        [dados["lotes"]]
    ], colWidths=[480])

    tabela_lotes.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    elementos.append(tabela_lotes)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Totais", styles["Heading3"]))

    tabela_totais = Table([
        ["Total de peças", "Total de peso (kg)", "Valor total (R$)"],
        [
            str(dados["total_pecas"]),
            f"{dados['total_peso']:.2f}",
            f"{dados['valor_total']:.2f}"
        ]
    ], colWidths=[160, 160, 160])

    tabela_totais.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela_totais)
    elementos.append(Spacer(1, 40))

    tabela_assinaturas = Table([
        ["_________________________", "_________________________", "_________________________"],
        ["Conferente", "Transporte", "Cliente"]
    ], colWidths=[160, 160, 160])

    tabela_assinaturas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    elementos.append(tabela_assinaturas)

    doc.build(elementos)

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER


def gerar_pdf_romaneio(dados, caminho_arquivo):
    doc = SimpleDocTemplate(
        caminho_arquivo,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()
    elementos = []

    titulo_style = ParagraphStyle(
        name="TituloCentral",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        spaceAfter=6
    )

    subtitulo_style = ParagraphStyle(
        name="SubtituloCentral",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=12
    )

    elementos.append(Paragraph("ROMANEIO", titulo_style))
    elementos.append(Paragraph("Sistema de Produção da Malharia", subtitulo_style))

    tabela_meta = Table([
        ["Nº do Romaneio", str(dados["romaneio_id"])],
        ["Data", dados["data"]],
    ], colWidths=[150, 330])

    tabela_meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elementos.append(tabela_meta)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Informações Gerais", styles["Heading3"]))

    tabela_info = Table([
        ["Máquina", dados["maquina"]],
        ["Artigo", dados["artigo"]],
    ], colWidths=[150, 330])

    tabela_info.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela_info)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Lotes do Romaneio", styles["Heading3"]))

    tabela_lotes = Table([
        [dados["lotes"]]
    ], colWidths=[480])

    tabela_lotes.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("PADDING", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ]))
    elementos.append(tabela_lotes)
    elementos.append(Spacer(1, 16))

    elementos.append(Paragraph("Totais", styles["Heading3"]))

    tabela_totais = Table([
        ["Total de peças", "Total de peso (kg)", "Valor total (R$)"],
        [
            str(dados["total_pecas"]),
            f"{dados['total_peso']:.2f}",
            f"{dados['valor_total']:.2f}"
        ]
    ], colWidths=[160, 160, 160])

    tabela_totais.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela_totais)
    elementos.append(Spacer(1, 40))

    tabela_assinaturas = Table([
        ["_________________________", "_________________________", "_________________________"],
        ["Conferente", "Transporte", "Cliente"]
    ], colWidths=[160, 160, 160])

    tabela_assinaturas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, 1), "Helvetica"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))
    elementos.append(tabela_assinaturas)

    doc.build(elementos)


# ================= USUÁRIOS =================

def buscar_usuario_por_username(db: Session, username: str):
    return db.query(models.Usuario).filter(
        models.Usuario.username == username
    ).first()


def criar_usuario_admin(db: Session, username: str, senha: str):
    usuario_existente = buscar_usuario_por_username(db, username)

    if usuario_existente:
        return usuario_existente

    senha_hash = pwd_context.hash(senha)

    novo_usuario = models.Usuario(
        username=username,
        senha_hash=senha_hash,
        ativo=True
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return novo_usuario


def autenticar_usuario(db: Session, username: str, senha: str):
    usuario = buscar_usuario_por_username(db, username)

    if not usuario:
        return None

    if not usuario.ativo:
        return None

    if not pwd_context.verify(senha, usuario.senha_hash):
        return None

    return usuario

def excluir_usuario_por_username(db: Session, username: str):
    usuario = db.query(models.Usuario).filter(
        models.Usuario.username == username
    ).first()

    if usuario:
        db.delete(usuario)
        db.commit()

# ================= FATURAMENTO =================

def criar_faturamento_extra(db: Session, data: str, descricao: str, valor: float):
    novo = models.FaturamentoExtra(
        data=data,
        descricao=descricao,
        valor=valor
    )

    db.add(novo)
    db.commit()
    db.refresh(novo)

    return novo


def listar_faturamentos_extras_por_mes(db: Session, ano: int, mes: int):
    prefixo_data = f"{ano}-{mes:02d}-"

    return db.query(models.FaturamentoExtra).filter(
        models.FaturamentoExtra.data.like(f"{prefixo_data}%")
    ).order_by(
        models.FaturamentoExtra.data,
        models.FaturamentoExtra.id
    ).all()


def total_extras_do_dia(db: Session, data: str):
    extras = db.query(models.FaturamentoExtra).filter(
        models.FaturamentoExtra.data == data
    ).all()

    return sum(float(extra.valor) for extra in extras)


def descricoes_extras_do_dia(db: Session, data: str):
    extras = db.query(models.FaturamentoExtra).filter(
        models.FaturamentoExtra.data == data
    ).all()

    descricoes = [extra.descricao.strip() for extra in extras if extra.descricao]

    return descricoes