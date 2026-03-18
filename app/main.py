import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.models import Producao
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import text

from app.database import Base, engine, SessionLocal
import app.models
from app import crud

Base.metadata.create_all(bind=engine)
admin_user = os.getenv("ADMIN_USER")
admin_password = os.getenv("ADMIN_PASSWORD")

if admin_user and admin_password:
    db_init = SessionLocal()
    try:
        crud.criar_usuario_admin(db_init, admin_user, admin_password)
    finally:
        db_init.close()
# db_init = SessionLocal()
# try:
#     crud.excluir_usuario_por_username(db_init, "admin")
#     crud.criar_usuario_admin(db_init, "admin", "1234")
# finally:
#     db_init.close()

# adiciona coluna "fechado" se ainda não existir (SQLite)
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE baixas_lotes ADD COLUMN fechado BOOLEAN DEFAULT 0"))
        conn.commit()
    except Exception:
        pass

app = FastAPI(title="Sistema de Produção da Malharia")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "malharia-chave-secreta-2026")
)
templates = Jinja2Templates(directory="templates")

def verificar_login(request: Request):
    usuario = request.session.get("usuario")
    if not usuario:
        return False
    return True


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    from datetime import datetime

    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    hoje = datetime.now()

    data_hoje_iso = hoje.strftime("%Y-%m-%d")
    data_brasil = hoje.strftime("%d/%m/%Y")

    db = SessionLocal()
    try:
        total_dia = crud.total_do_dia(db, data_hoje_iso)
        valor_total_dia = crud.valor_total_do_dia(db, data_hoje_iso)
        total_pecas, total_peso = crud.resumo_estoque(db)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "data_hoje": data_brasil,
                "total_dia": total_dia,
                "valor_total_dia": valor_total_dia,
                "total_pecas": total_pecas,
                "total_peso": total_peso
            }
        )
    finally:
        db.close()


@app.get("/login", response_class=HTMLResponse)
def tela_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "erro": ""
        }
    )


@app.post("/login", response_class=HTMLResponse)
def fazer_login(
    request: Request,
    username: str = Form(...),
    senha: str = Form(...)
):
    db = SessionLocal()
    try:
        usuario = crud.autenticar_usuario(db, username, senha)

        if not usuario:
            return templates.TemplateResponse(
                "login.html",
                {
                    "request": request,
                    "erro": "Usuário ou senha inválidos."
                }
            )

        request.session["usuario"] = usuario.username

        return RedirectResponse(url="/", status_code=303)
    finally:
        db.close()


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)

# ================= CLIENTES =================

@app.get("/clientes", response_class=HTMLResponse)
def tela_clientes(request: Request):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        clientes = crud.listar_clientes(db)
        return templates.TemplateResponse(
            "clientes.html",
            {"request": request, "clientes": clientes}
        )
    finally:
        db.close()


@app.post("/clientes", response_class=HTMLResponse)
def salvar_cliente(request: Request, nome: str = Form(...)):
    db = SessionLocal()
    try:
        crud.criar_cliente(db, nome)
        clientes = crud.listar_clientes(db)

        return templates.TemplateResponse(
            "clientes.html",
            {"request": request, "clientes": clientes}
        )
    finally:
        db.close()


# ================= ARTIGOS =================

@app.get("/artigos", response_class=HTMLResponse)
def tela_artigos(request: Request):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        artigos = crud.listar_artigos(db)
        clientes = crud.listar_clientes(db)

        return templates.TemplateResponse(
            "artigos.html",
            {
                "request": request,
                "artigos": artigos,
                "clientes": clientes
            }
        )
    finally:
        db.close()


@app.post("/artigos", response_class=HTMLResponse)
def salvar_artigo(
    request: Request,
    nome: str = Form(...),
    codigo: str = Form(...),
    valor_kg: float = Form(...),
    cliente_id: int = Form(...)
):
    db = SessionLocal()
    try:
        crud.criar_artigo(db, nome, codigo, valor_kg, cliente_id)

        artigos = crud.listar_artigos(db)
        clientes = crud.listar_clientes(db)

        return templates.TemplateResponse(
            "artigos.html",
            {
                "request": request,
                "artigos": artigos,
                "clientes": clientes
            }
        )
    finally:
        db.close()


# ================= MÁQUINAS =================

@app.get("/maquinas", response_class=HTMLResponse)
def tela_maquinas(request: Request):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        maquinas = crud.listar_maquinas(db)

        return templates.TemplateResponse(
            "maquinas.html",
            {
                "request": request,
                "maquinas": maquinas
            }
        )
    finally:
        db.close()


@app.post("/maquinas", response_class=HTMLResponse)
def salvar_maquina(request: Request, nome: str = Form(...)):
    db = SessionLocal()
    try:
        crud.criar_maquina(db, nome)

        maquinas = crud.listar_maquinas(db)

        return templates.TemplateResponse(
            "maquinas.html",
            {
                "request": request,
                "maquinas": maquinas
            }
        )
    finally:
        db.close()


# ================= PRODUÇÃO =================

@app.get("/producao", response_class=HTMLResponse)
def tela_producao(request: Request):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        producoes = crud.listar_producoes(db)
        maquinas = crud.listar_maquinas(db)
        artigos = crud.listar_artigos(db)

        data_hoje = ""
        total_1_turno = 0
        total_2_turno = 0
        total_3_turno = 0
        total_dia = 0
        valor_total_dia = 0
        resumo_maquinas = {}

        if producoes:
            data_hoje = producoes[-1].data

            total_1_turno = crud.total_por_turno(db, data_hoje, "1º turno")
            total_2_turno = crud.total_por_turno(db, data_hoje, "2º turno")
            total_3_turno = crud.total_por_turno(db, data_hoje, "3º turno")
            total_dia = crud.total_do_dia(db, data_hoje)
            valor_total_dia = crud.valor_total_do_dia(db, data_hoje)
            resumo_maquinas = crud.resumo_por_maquina_no_dia(db, data_hoje)

        return templates.TemplateResponse(
            "producao.html",
            {
                "request": request,
                "producoes": producoes,
                "maquinas": maquinas,
                "artigos": artigos,
                "data_hoje": data_hoje,
                "total_1_turno": total_1_turno,
                "total_2_turno": total_2_turno,
                "total_3_turno": total_3_turno,
                "total_dia": total_dia,
                "valor_total_dia": valor_total_dia,
                "resumo_maquinas": resumo_maquinas
            }
        )
    finally:
        db.close()


@app.post("/producao", response_class=HTMLResponse)
def salvar_producao(
    request: Request,
    data: str = Form(...),
    turno: str = Form(...),
    maquina_id: int = Form(...),
    artigo_id: int = Form(...),
    lote: str = Form(...),
    peso: str = Form(...)
):
    peso_texto = peso.replace(",", ".").replace(" ", "")

    if "+" in peso_texto:
        partes = [p for p in peso_texto.split("+") if p]
        peso_calculado = sum(float(parte) for parte in partes)
        pecas = len(partes)
    else:
        peso_calculado = float(peso_texto)
        pecas = 1

    db = SessionLocal()
    try:
        crud.criar_producao(
            db, data, turno, maquina_id,
            artigo_id, lote, pecas, peso_calculado
        )

        producoes = crud.listar_producoes(db)
        maquinas = crud.listar_maquinas(db)
        artigos = crud.listar_artigos(db)

        data_hoje = ""
        total_1_turno = 0
        total_2_turno = 0
        total_3_turno = 0
        total_dia = 0
        valor_total_dia = 0
        resumo_maquinas = {}

        if producoes:
            data_hoje = producoes[-1].data
            total_1_turno = crud.total_por_turno(db, data_hoje, "1º turno")
            total_2_turno = crud.total_por_turno(db, data_hoje, "2º turno")
            total_3_turno = crud.total_por_turno(db, data_hoje, "3º turno")
            total_dia = crud.total_do_dia(db, data_hoje)
            valor_total_dia = crud.valor_total_do_dia(db, data_hoje)
            resumo_maquinas = crud.resumo_por_maquina_no_dia(db, data_hoje)

        return templates.TemplateResponse(
            "producao.html",
            {
                "request": request,
                "producoes": producoes,
                "maquinas": maquinas,
                "artigos": artigos,
                "data_hoje": data_hoje,
                "total_1_turno": total_1_turno,
                "total_2_turno": total_2_turno,
                "total_3_turno": total_3_turno,
                "total_dia": total_dia,
                "valor_total_dia": valor_total_dia,
                "resumo_maquinas": resumo_maquinas
            }
        )
    finally:
        db.close()


# ================= LOTES =================

@app.get("/lotes", response_class=HTMLResponse)
def tela_lotes(request: Request):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        producoes = crud.listar_producoes(db)
        total_pecas, total_peso = crud.resumo_estoque(db)
        estoque_artigos = crud.estoque_por_artigo(db)
        estoque_clientes = crud.estoque_por_cliente(db)

        resumo_maquinas = {}

        return templates.TemplateResponse(
            "lotes.html",
            {
                "request": request,
                "producoes": producoes,
                "total_pecas": total_pecas,
                "total_peso": total_peso,
                "estoque_artigos": estoque_artigos,
                "estoque_clientes": estoque_clientes,
                "resumo_maquinas": resumo_maquinas
            }
        )
    finally:
        db.close()


@app.post("/baixar_lote")
def baixar_lote(
    producao_id: int = Form(...),
    pecas: int = Form(...)
):
    db = SessionLocal()
    try:
        crud.baixar_lote(db, producao_id, pecas)
        return RedirectResponse(url="/lotes", status_code=303)
    finally:
        db.close()


@app.post("/ajustar_lote")
def ajustar_lote(
    producao_id: int = Form(...),
    novo_saldo: int = Form(...)
):
    db = SessionLocal()
    try:
        crud.ajustar_saldo_lote(db, producao_id, novo_saldo)
        return RedirectResponse(url="/lotes", status_code=303)
    finally:
        db.close()


# ================= ROMANEIO =================

@app.get("/romaneio", response_class=HTMLResponse)
def tela_romaneio(request: Request):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    db = SessionLocal()
    try:
        dados = crud.gerar_romaneio(db)

        if not dados:
            return HTMLResponse("Nenhuma baixa registrada ainda.")

        return templates.TemplateResponse(
            "romaneio.html",
            {
                "request": request,
                "romaneio_id": dados["romaneio_id"],
                "data_hoje": dados["data"],
                "maquina": dados["maquina"],
                "artigo": dados["artigo"],
                "lotes": dados["lotes"],
                "total_pecas": dados["total_pecas"],
                "total_peso": dados["total_peso"],
                "valor_total": dados["valor_total"]
            }
        )
    finally:
        db.close()


@app.get("/romaneio/pdf")
def baixar_pdf_romaneio():
    db = SessionLocal()
    try:
        dados = crud.gerar_romaneio(db)

        if not dados:
            return HTMLResponse("Nenhum romaneio disponível.")

        caminho = "romaneio.pdf"

        crud.gerar_pdf_romaneio(dados, caminho)

        return FileResponse(
            path=caminho,
            filename="romaneio.pdf",
            media_type="application/pdf"
        )
    finally:
        db.close()


@app.post("/concluir_romaneio")
def concluir_romaneio():
    db = SessionLocal()
    try:
        crud.concluir_romaneio(db)
        return RedirectResponse(url="/lotes", status_code=303)
    finally:
        db.close()

@app.get("/relatorio", response_class=HTMLResponse)
def tela_relatorio(request: Request, mes: int = None, ano: int = None):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    from datetime import datetime
    import calendar

    hoje = datetime.now()

    if not mes:
        mes = hoje.month

    if not ano:
        ano = hoje.year

    nomes_meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro"
    }

    nome_mes = nomes_meses.get(mes, "")

    dias_no_mes = calendar.monthrange(ano, mes)[1]

    db = SessionLocal()
    try:
        maquinas = crud.listar_maquinas(db)

        # ================= RELATÓRIO MENSAL =================
        relatorio = []

        totais_maquina = {m.nome: 0 for m in maquinas}
        total_geral_mes = 0

        for dia in range(1, dias_no_mes + 1):

            data = f"{ano}-{mes:02d}-{dia:02d}"

            linha = {
                "dia": dia,
                "maquinas": {},
                "total_dia": 0
            }

            for maquina in maquinas:

                producoes = db.query(Producao).filter(
                    Producao.data == data,
                    Producao.maquina_id == maquina.id
                ).all()

                turno1 = sum(float(p.peso) for p in producoes if p.turno == "1º turno")
                turno2 = sum(float(p.peso) for p in producoes if p.turno == "2º turno")
                turno3 = sum(float(p.peso) for p in producoes if p.turno == "3º turno")

                total_maquina = turno1 + turno2 + turno3

                linha["maquinas"][maquina.nome] = {
                    "t1": turno1,
                    "t2": turno2,
                    "t3": turno3,
                    "total": total_maquina
                }

                linha["total_dia"] += total_maquina
                totais_maquina[maquina.nome] += total_maquina
                total_geral_mes += total_maquina

            relatorio.append(linha)

        # ================= RELATÓRIO ANUAL =================
        relatorio_anual = []
        totais_anuais_maquina = {m.nome: 0 for m in maquinas}
        total_geral_ano = 0

        for mes_ref in range(1, 13):

            dias_mes_ref = calendar.monthrange(ano, mes_ref)[1]

            linha_anual = {
                "mes_numero": mes_ref,
                "mes_nome": nomes_meses[mes_ref],
                "maquinas": {},
                "total_mes": 0
            }

            for maquina in maquinas:
                total_maquina_mes = 0

                for dia in range(1, dias_mes_ref + 1):
                    data = f"{ano}-{mes_ref:02d}-{dia:02d}"

                    producoes = db.query(Producao).filter(
                        Producao.data == data,
                        Producao.maquina_id == maquina.id
                    ).all()

                    total_maquina_mes += sum(float(p.peso) for p in producoes)

                linha_anual["maquinas"][maquina.nome] = total_maquina_mes
                linha_anual["total_mes"] += total_maquina_mes
                totais_anuais_maquina[maquina.nome] += total_maquina_mes
                total_geral_ano += total_maquina_mes

            relatorio_anual.append(linha_anual)

        grafico_meses = {
            linha["mes_nome"]: linha["total_mes"]
            for linha in relatorio_anual
        }

        total_turno1 = 0
        total_turno2 = 0
        total_turno3 = 0

        for linha in relatorio:
            for dados in linha["maquinas"].values():
                total_turno1 += dados["t1"]
                total_turno2 += dados["t2"]
                total_turno3 += dados["t3"]

        grafico_turnos = {
            "1º turno": total_turno1,
            "2º turno": total_turno2,
            "3º turno": total_turno3
        }

        grafico_maquinas = {
            maquina.nome: totais_maquina[maquina.nome]
            for maquina in maquinas
        }
        return templates.TemplateResponse(
            "relatorio.html",
            {
                "request": request,
                "mes": mes,
                "ano": ano,
                "nome_mes": nome_mes,
                "maquinas": maquinas,
                "relatorio": relatorio,
                "totais_maquina": totais_maquina,
                "total_geral_mes": total_geral_mes,
                "relatorio_anual": relatorio_anual,
                "totais_anuais_maquina": totais_anuais_maquina,
                "total_geral_ano": total_geral_ano,
                "grafico_maquinas": grafico_maquinas,
                "grafico_meses": grafico_meses,
                "grafico_turnos": grafico_turnos
            }
        )

    finally:
        db.close()

@app.get("/faturamento", response_class=HTMLResponse)
def tela_faturamento(request: Request, mes: int = None, ano: int = None):

    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    from datetime import datetime
    import calendar

    hoje = datetime.now()

    if not mes:
        mes = hoje.month

    if not ano:
        ano = hoje.year

    nomes_meses = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Março",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro"
    }

    nome_mes = nomes_meses.get(mes, "")

    dias_no_mes = calendar.monthrange(ano, mes)[1]

    db = SessionLocal()
    try:
        faturamento_dias = []
        total_mes = 0

        for dia in range(1, dias_no_mes + 1):
            data = f"{ano}-{mes:02d}-{dia:02d}"

            valor_producao = crud.valor_total_do_dia(db, data)
            valor_extras = crud.total_extras_do_dia(db, data)
            total_dia = float(valor_producao) + float(valor_extras)

            descricoes = []

            if float(valor_producao) > 0:
                descricoes.append("Produção")

            descricoes_extras = crud.descricoes_extras_do_dia(db, data)

            for descricao in descricoes_extras:
                if descricao not in descricoes:
                    descricoes.append(descricao)

            descricao_final = " + ".join(descricoes) if descricoes else "-"

            faturamento_dias.append({
                "dia": dia,
                "data": data,
                "descricao": descricao_final,
                "valor_producao": valor_producao,
                "valor_extras": valor_extras,
                "total_dia": total_dia
            })

            total_mes += total_dia

        # ===== RESUMO DOS ÚLTIMOS 12 MESES =====

        resumo_12_meses = []
        total_12_meses = 0

        nomes_meses = {
            1: "Janeiro",
            2: "Fevereiro",
            3: "Março",
            4: "Abril",
            5: "Maio",
            6: "Junho",
            7: "Julho",
            8: "Agosto",
            9: "Setembro",
            10: "Outubro",
            11: "Novembro",
            12: "Dezembro"
        }

        # COMEÇAR NO ÚLTIMO MÊS COMPLETO
        mes_temp = mes - 1
        ano_temp = ano

        if mes_temp == 0:
            mes_temp = 12
            ano_temp -= 1

        for _ in range(12):
            dias_mes_temp = calendar.monthrange(ano_temp, mes_temp)[1]
            total_mes_temp = 0

            for dia in range(1, dias_mes_temp + 1):
                data_temp = f"{ano_temp}-{mes_temp:02d}-{dia:02d}"

                valor_producao = crud.valor_total_do_dia(db, data_temp)
                valor_extras = crud.total_extras_do_dia(db, data_temp)

                total_mes_temp += float(valor_producao) + float(valor_extras)

            resumo_12_meses.append({
                "mes_numero": mes_temp,
                "mes_nome": nomes_meses.get(mes_temp, ""),
                "ano": ano_temp,
                "total": total_mes_temp
            })

            total_12_meses += total_mes_temp

            mes_temp -= 1
            if mes_temp == 0:
                mes_temp = 12
                ano_temp -= 1

        resumo_12_meses = sorted(
            resumo_12_meses,
            key=lambda item: (item["ano"], item["mes_numero"])
        )

        media_mensal = total_12_meses / 12 if total_12_meses else 0

        # ===== PROJEÇÃO DO MÊS ATUAL =====
        from datetime import datetime

        hoje_real = datetime.now()
        data_hoje_str = hoje_real.strftime("%Y-%m-%d")

        faturado_mes_atual = 0
        dias_decorridos = 0
        dias_mes_atual = calendar.monthrange(ano, mes)[1]

        if ano == hoje_real.year and mes == hoje_real.month:
            dias_decorridos = hoje_real.day
        else:
            dias_decorridos = dias_mes_atual

        for dia in range(1, dias_decorridos + 1):
            data_temp = f"{ano}-{mes:02d}-{dia:02d}"

            valor_producao = crud.valor_total_do_dia(db, data_temp)
            valor_extras = crud.total_extras_do_dia(db, data_temp)

            faturado_mes_atual += float(valor_producao) + float(valor_extras)

        media_diaria_atual = faturado_mes_atual / dias_decorridos if dias_decorridos > 0 else 0
        projecao_mes_atual = media_diaria_atual * dias_mes_atual

        # ===== COMPARATIVO PRODUÇÃO X FATURAMENTO =====
        total_producao_mes_kg = 0

        for dia in range(1, dias_no_mes + 1):
            data_temp = f"{ano}-{mes:02d}-{dia:02d}"
            total_producao_mes_kg += float(crud.total_do_dia(db, data_temp))

        return templates.TemplateResponse(
            "faturamento.html",
            {
                "request": request,
                "mes": mes,
                "ano": ano,
                "nome_mes": nome_mes,
                "faturamento_dias": faturamento_dias,
                "total_mes": total_mes,
                "resumo_12_meses": resumo_12_meses,
                "total_12_meses": total_12_meses,
                "media_mensal": media_mensal,
                "grafico_12_meses": resumo_12_meses,
                "faturado_mes_atual": faturado_mes_atual,
                "dias_decorridos": dias_decorridos,
                "dias_mes_atual": dias_mes_atual,
                "media_diaria_atual": media_diaria_atual,
                "projecao_mes_atual": projecao_mes_atual,
                "total_producao_mes_kg": total_producao_mes_kg
            }
        )
    finally:
        db.close()


@app.post("/faturamento/extra")
def salvar_faturamento_extra(
    request: Request,
    data: str = Form(...),
    descricao: str = Form(...),
    valor: str = Form(...)
):
    if not verificar_login(request):
        return RedirectResponse(url="/login", status_code=303)

    valor_texto = valor.replace(".", "").replace(",", ".").replace(" ", "")

    db = SessionLocal()
    try:
        crud.criar_faturamento_extra(db, data, descricao, float(valor_texto))
        return RedirectResponse(url="/faturamento", status_code=303)
    finally:
        db.close()