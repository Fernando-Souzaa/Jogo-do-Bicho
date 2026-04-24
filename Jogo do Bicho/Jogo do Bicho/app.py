import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="1234",
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
        criar_evento()

def criar_evento(nome):
    conexao = get_db_connection()
    cursor = conexao.cursor()

    sql = "INSERT INTO eventos (nome, data_evento, status) VALUES (%s, NOW(), 'ABERTO')"
    cursor.execute(sql, (nome,))

    conexao.commit()
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
            return redirect("/home")

    return render_template("login.html")

# ---------------- HOME (APOSTA) ----------------
@app.route("/home", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    # buscar eventos
    cursor.execute("SELECT * FROM eventos WHERE status='ABERTO'")
    eventos = cursor.fetchall()

    erro = None

    if request.method == "POST":
        evento_id = request.form.get("evento_id")
        grupo = request.form.get("grupo")
        dezena = request.form.get("dezena")

        valor = request.form.get("valor_grupo") or request.form.get("valor_dezena")

        if not evento_id:
            erro = "Evento não selecionado!"

        elif not valor:
            erro = "Informe um valor!"

        elif not grupo and not dezena:
            erro = "Informe grupo ou dezena!"

        else:
            if grupo:
                tipo = "GRUPO"
            else:
                tipo = "DEZENA"

            cursor.execute("""
                INSERT INTO apostas 
                (usuario_id, evento_id, grupo, dezena, tipo, valor, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'PENDENTE')
            """, (
                session["user"]["id"],
                evento_id,
                grupo,
                dezena,
                tipo,
                valor
            ))

            conexao.commit()

    cursor.close()
    conexao.close()

    return render_template("home.html", eventos=eventos, erro=erro)
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
def resultados_page():
    if "user" not in session:
        return redirect("/login")

    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)

    agora = datetime.now()
    hora_atual = agora.strftime("%H:%M")

    cursor.execute("SELECT * FROM eventos")
    eventos = cursor.fetchall()

    lista_resultados = []

    for evento in eventos:
        nome = evento["nome"]

        # extrai hora do nome (ex: "Jogo do Bicho - 11:00")
        hora_evento = nome.split("-")[1].strip()

        if hora_evento <= hora_atual:

            if evento["grupo_resultado"] is None:
                grupo, dezena = gerar_resultado()

                salvar_resultado(evento["id"], grupo, dezena)
            else:
                grupo = evento["grupo_resultado"]
                dezena = evento["dezena_resultado"]

            lista_resultados.append({
                "hora": hora_evento,
                "grupo": grupo,
                "dezena": dezena,
                "liberado": True
            })

        else:
            lista_resultados.append({
                "hora": hora_evento,
                "grupo": "",
                "dezena": "",
                "liberado": False
            })

    cursor.close()
    conexao.close()

    verificar_apostas()

    return render_template("resultados.html", resultados=lista_resultados)
# ---------------- PERFIL ----------------
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    if "user" not in session:
        return redirect("/login")

    user = session["user"]

    if request.method == "POST":
        foto = request.files["foto"]

        if foto:
            caminho = os.path.join(app.config["UPLOAD_FOLDER"], foto.filename)
            foto.save(caminho)
            user["foto"] = caminho

    return render_template("perfil.html", user=user)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")

# ---------------- RODAR ----------------
if __name__ == "__main__":
    app.run(debug=True)
