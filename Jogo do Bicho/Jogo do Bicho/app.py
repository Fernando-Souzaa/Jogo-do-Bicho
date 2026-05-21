import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="100907",
        database="banco_dados"
    )

from flask import Flask, render_template, request, redirect, session
import os
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "segredo"

# upload
UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# horários reais
horarios = ["11:00", "14:00", "16:00", "18:00"]

def criar_eventos_do_dia():
    for hora in horarios:
        nome = f"Jogo do Bicho - {hora}"
        criar_evento(nome)

def criar_evento(nome):

    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    # VERIFICA SE JÁ EXISTE EVENTO ABERTO COM ESSE NOME
    cursor.execute("""
        SELECT id
        FROM eventos
        WHERE nome = %s
        AND status = 'ABERTO'
    """, (nome,))

    evento_existente = cursor.fetchone()

    # SÓ CRIA SE NÃO EXISTIR
    if not evento_existente:

        cursor.execute("""
            INSERT INTO eventos
            (
                nome,
                data_evento,
                status
            )
            VALUES (%s, NOW(), 'ABERTO')
        """, (nome,))

        conexao.commit()

        print("EVENTO CRIADO:", nome)

    else:

        print("EVENTO JÁ EXISTE:", nome)

    cursor.close()
    conexao.close()

# resultados gerados
resultados = {}

# ---------------- GERAR RESULTADO ----------------
def gerar_resultado():
    grupo = random.randint(1, 25)
    dezena = random.randint(0, 99)
    return grupo, f"{dezena:02d}"

def salvar_resultado(evento_id, grupo, dezena):
    conexao = get_db_connection()
    cursor = conexao.cursor()


    print("ENCERRANDO EVENTO:", evento_id)
    cursor.execute("""
        UPDATE eventos
        SET grupo_resultado = %s,
            dezena_resultado = %s,
            status = 'ENCERRADO'
        WHERE id = %s
    """, (grupo, dezena, evento_id))

    conexao.commit()
    cursor.close()
    conexao.close()

# ---------------- INICIO ----------------
@app.route("/")
def index():
    return redirect("/login")

# ---------------- CADASTRO ----------------
@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        senha = request.form["senha"]

        conexao = get_db_connection()
        cursor = conexao.cursor()

        sql = "INSERT INTO usuarios (nome, email, senha) VALUES (%s, %s, %s)"
        valores = (nome, email, senha)

        cursor.execute(sql, valores)
        conexao.commit()

        cursor.close()
        conexao.close()

        return redirect("/login")

    return render_template("cadastro.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        conexao = get_db_connection()
        cursor = conexao.cursor(dictionary=True)

        sql = "SELECT * FROM usuarios WHERE email=%s AND senha=%s"
        cursor.execute(sql, (email, senha))

        user = cursor.fetchone()

        cursor.close()
        conexao.close()

        if user:
            session["user"] = user

            user["saldo"] = float(user["saldo"])

            return redirect("/home")

    return render_template("login.html")

# ---------------- HOME (APOSTA) ----------------
@app.route("/home", methods=["GET", "POST"])
def home():

    if "user" not in session:
        return redirect("/login")

    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    # EVENTOS
    cursor.execute("""
        SELECT * FROM eventos
        WHERE status='ABERTO'
    """)

    eventos = cursor.fetchall()

    erro = None

    if request.method == "POST":

        evento_id = request.form.get("evento_id")

        grupo = request.form.get("grupo")
        dezena = request.form.get("dezena")

        valor_grupo = request.form.get("valor_grupo")
        valor_dezena = request.form.get("valor_dezena")

        print(request.form)

        if not evento_id:

            erro = "Evento não encontrado"

        elif not valor_grupo and not valor_dezena:

            erro = "Informe um valor"

        else:

            saldo_atual = float(session["user"]["saldo"])

            total_aposta = 0

            if valor_grupo:
                total_aposta += float(valor_grupo)

            if valor_dezena:
                total_aposta += float(valor_dezena)

            if saldo_atual < total_aposta:

                erro = "Saldo insuficiente"

            else:

                novo_saldo = saldo_atual - total_aposta

                # APOSTA EM GRUPO
                if grupo and valor_grupo:

                    valor_grupo = float(valor_grupo)

                    cursor.execute("""
                        INSERT INTO apostas
                        (
                            usuario_id,
                            evento_id,
                            grupo,
                            dezena,
                            tipo,
                            valor,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'PENDENTE')
                    """, (
                        session["user"]["id"],
                        evento_id,
                        grupo,
                        None,
                        "GRUPO",
                        valor_grupo
                    ))

                # APOSTA EM DEZENA
                if dezena and valor_dezena:

                    valor_dezena = float(valor_dezena)

                    cursor.execute("""
                        INSERT INTO apostas
                        (
                            usuario_id,
                            evento_id,
                            grupo,
                            dezena,
                            tipo,
                            valor,
                            status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'PENDENTE')
                    """, (
                        session["user"]["id"],
                        evento_id,
                        None,
                        dezena,
                        "DEZENA",
                        valor_dezena
                    ))

                # ATUALIZA SALDO
                cursor.execute("""
                    UPDATE usuarios
                    SET saldo = %s
                    WHERE id = %s
                """, (
                    novo_saldo,
                    session["user"]["id"]
                ))

                conexao.commit()

                print("APOSTA SALVA")

                # ATUALIZA SESSÃO
                session["user"]["saldo"] = float(novo_saldo)
                session.modified = True

                return redirect("/resultados")

    cursor.close()
    conexao.close()

    return render_template(
        "home.html",
        eventos=eventos,
        erro=erro,
        user=session["user"]
    )
# ---------------- ADICIONAR SALDO ----------------
@app.route("/adicionar_saldo", methods=["POST"])
def adicionar_saldo():

    print("ROTA FUNCIONOU")

    if "user" not in session:
        return redirect("/login")

    valor = request.form["valor"]

    if valor:
        valor = float(valor)
    else:
        valor = 0

    saldo_atual = float(session["user"]["saldo"])

    novo_saldo = saldo_atual + valor

    print("Saldo antigo:", saldo_atual)
    print("Novo saldo:", novo_saldo)

    conexao = get_db_connection()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET saldo = %s
        WHERE id = %s
    """, (
        novo_saldo,
        session["user"]["id"]
    ))

    conexao.commit()

    cursor.close()
    conexao.close()

    # Atualiza sessão
    session["user"]["saldo"] = novo_saldo

    session.modified = True

    return redirect("/home")

    
# ---------------- VERIFICAR GANHADORES ----------------
def verificar_apostas():
    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT a.*, e.grupo_resultado, e.dezena_resultado
        FROM apostas a
        JOIN eventos e ON a.evento_id = e.id
        WHERE a.status = 'PENDENTE'
    """)

    apostas = cursor.fetchall()

    for aposta in apostas:
        ganhou = False

        if aposta["tipo"] == "GRUPO" and aposta["grupo"] == aposta["grupo_resultado"]:
            ganhou = True

        elif aposta["tipo"] == "DEZENA" and aposta["dezena"] == aposta["dezena_resultado"]:
            ganhou = True

        novo_status = "GANHA" if ganhou else "PERDIDA"

        cursor.execute("""
            UPDATE apostas SET status = %s WHERE id = %s
        """, (novo_status, aposta["id"]))

    conexao.commit()
    cursor.close()
    conexao.close()

# ---------------- RESULTADOS ----------------
@app.route("/resultados")
def resultados():

    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    # BUSCA APENAS 1 EVENTO ABERTO
    cursor.execute("""
        SELECT * FROM eventos
        WHERE status = 'ABERTO'
        LIMIT 1
    """)

    evento = cursor.fetchone()

    if evento:

        grupo = random.randint(1, 25)
        dezena = str(random.randint(0, 99)).zfill(2)

        

        cursor.execute("""
            UPDATE eventos
            SET 
                grupo_resultado = %s,
                dezena_resultado = %s,
                status = 'ENCERRADO'
            WHERE id = %s
        """, (
            grupo,
            dezena,
            evento["id"]
        ))

        conexao.commit()

       # BUSCA APOSTAS DO EVENTO
        cursor.execute("""
            SELECT a.*, e.grupo_resultado, e.dezena_resultado
            FROM apostas a
            JOIN eventos e ON a.evento_id = e.id
            WHERE e.id = %s
        """, (evento["id"],))

        apostas = cursor.fetchall()

        for aposta in apostas:

            premio = 0
            status = "PERDIDA"

            # GANHOU NO GRUPO
            if (
                aposta["tipo"] == "GRUPO"
                and aposta["grupo"] == aposta["grupo_resultado"]
            ):

                premio = float(aposta["valor"]) * 18
                status = "GANHA"

            # GANHOU NA DEZENA
            elif (
                aposta["tipo"] == "DEZENA"
                and aposta["dezena"] == aposta["dezena_resultado"]
            ):

                premio = float(aposta["valor"]) * 60
                status = "GANHA"

            # ATUALIZA APOSTA
            cursor.execute("""
                UPDATE apostas
                SET
                    status = %s,
                    premio = %s
                WHERE id = %s
            """, (
                status,
                premio,
                aposta["id"]
            ))

            # SE GANHOU, ADICIONA AO SALDO
            if premio > 0:

                cursor.execute("""
                    UPDATE usuarios
                    SET saldo = saldo + %s
                    WHERE id = %s
                """, (
                    premio,
                    aposta["usuario_id"]
                ))


                    # ATUALIZA SESSÃO
            if aposta["usuario_id"] == session["user"]["id"]:

                session["user"]["saldo"] += premio
                session.modified = True
        conexao.commit()

        # VERIFICA SE EXISTEM EVENTOS ABERTOS
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM eventos
            WHERE status = 'ABERTO'
        """)

        total = cursor.fetchone()["total"]

        # SE NÃO EXISTIR EVENTO ABERTO
        if total == 0:

            # PEGA NOMES DOS EVENTOS ANTIGOS
            cursor.execute("""
                SELECT DISTINCT nome
                FROM eventos
                GROUP BY nome
            """)

            eventos_anteriores = cursor.fetchall()

            # RECRIA EVENTOS
            for evento_anterior in eventos_anteriores:

                cursor.execute("""
                    INSERT INTO eventos
                    (
                        nome,
                        status
                    )
                    VALUES (%s, 'ABERTO')
                """, (
                    evento_anterior["nome"],
                ))

            conexao.commit()

            print("NOVOS EVENTOS GERADOS")

    # BUSCA RESULTADOS
    cursor.execute("""
        SELECT *
        FROM eventos
        ORDER BY id DESC
    """)

    resultados = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "resultados.html",
        resultados=resultados
    )
# ---------------- PERFIL ----------------
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "user" not in session:
        return redirect("/login")

    user = session["user"]

    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    # FOTO
    if request.method == "POST":
        foto = request.files["foto"]

        if foto:
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], foto.filename)
            foto.save(caminho)
            user["foto"] = caminho

    # BUSCAR HISTÓRICO
    cursor.execute("""
        SELECT 
            a.tipo,
            a.grupo,
            a.dezena,
            a.valor,       
            a.status,
            e.nome AS evento,       
            DATE(a.criado_em) AS data,
            TIME(a.criado_em) AS horario,
            a.premio
        FROM apostas a
        JOIN eventos e ON e.id = a.evento_id           
        WHERE a.usuario_id = %s
        ORDER BY a.criado_em DESC
    """, (user["id"],))

    historico = cursor.fetchall()

    print(historico)

    cursor.close()
    conexao.close()

    return render_template(
        "perfil.html",
        user=user,
        historico=historico
    )
# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------------- RODAR ----------------
if __name__ == "__main__":
    app.run(debug=True)
