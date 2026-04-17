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

# "banco fake"
usuarios = []
apostas = []

# horários reais
horarios = ["11:00", "14:00", "16:00", "18:00"]

# resultados gerados
resultados = {}

# ---------------- GERAR RESULTADO ----------------
def gerar_resultado():
    grupo = random.randint(1, 25)
    dezena = random.randint(0, 99)
    return grupo, f"{dezena:02d}"

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

        usuarios.append({
            "nome": nome,
            "email": email,
            "senha": senha,
            "foto": None,
            "historico": []
        })

        return redirect("/login")

    return render_template("cadastro.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        senha = request.form["senha"]

        for user in usuarios:
            if user["email"] == email and user["senha"] == senha:
                session["user"] = user
                return redirect("/home")

    return render_template("login.html")

# ---------------- HOME (APOSTA) ----------------
@app.route("/home", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect("/login")

    erro = None

    if request.method == "POST":
        grupo = request.form.get("grupo")
        valor_grupo = request.form.get("valor_grupo")
        dezena = request.form.get("dezena")
        valor_dezena = request.form.get("valor_dezena")
        horario = request.form["horario"]
        data = request.form["data"]

        if not grupo and not dezena:
            erro = "Escolha grupo ou dezena!"
        else:
            aposta = {
                "grupo": grupo,
                "valor_grupo": valor_grupo,
                "dezena": dezena,
                "valor_dezena": valor_dezena,
                "horario": horario,
                "data": data,
                "resultado": "Aguardando"
            }

            session["user"]["historico"].append(aposta)
            apostas.append(aposta)

    return render_template("home.html", erro=erro)

# ---------------- VERIFICAR GANHADORES ----------------
def verificar_apostas():
    for user in usuarios:
        for aposta in user["historico"]:

            horario = aposta["horario"]

            if horario in resultados and aposta["resultado"] == "Aguardando":
                grupo_resultado, dezena_resultado = resultados[horario]

                ganhou = False

                if aposta["grupo"]:
                    if int(aposta["grupo"]) == grupo_resultado:
                        ganhou = True

                if aposta["dezena"]:
                    if aposta["dezena"] == dezena_resultado:
                        ganhou = True

                aposta["resultado"] = "Ganhou 🏆" if ganhou else "Perdeu ❌"

# ---------------- RESULTADOS ----------------
@app.route("/resultados")
def resultados_page():
    if "user" not in session:
        return redirect("/login")

    agora = datetime.now()
    hora_atual = agora.strftime("%H:%M")
    data_hoje = agora.strftime("%d/%m/%Y")

    lista_resultados = []

    for hora in horarios:

        if hora <= hora_atual:
            if hora not in resultados:
                resultados[hora] = gerar_resultado()

            grupo, dezena = resultados[hora]

            lista_resultados.append({
                "hora": hora,
                "grupo": grupo,
                "dezena": dezena,
                "liberado": True
            })
        else:
            lista_resultados.append({
                "hora": hora,
                "grupo": "",
                "dezena": "",
                "liberado": False
            })

    verificar_apostas()

    return render_template(
        "resultados.html",
        resultados=lista_resultados,
        data_hoje=data_hoje
    )
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