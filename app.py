import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# ⚠️ LINK DA SUA INSTÂNCIA DA Z-API (Substitua tudo o que está entre as aspas pelo seu link do "send-text")
Z_API_URL = "COLE_AQUI_O_LINK_COMPLETO_DO_SEND_TEXT_DA_ZAP"

def consultar_cnpj(cnpj):
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    url = f"https://receitaws.com.br{cnpj_limpo}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("status") == "ERROR":
                return "❌ CNPJ inválido ou não encontrado na base de dados pública."

            nome = dados.get("nome")
            abertura = dados.get("abertura")
            situacao = dados.get("situacao")
            capital = dados.get("capital_social", "0.00")

            resposta = (
                f"📊 *ANÁLISE DE CRÉDITO IMEDIATA*\n\n"
                f"🏢 *Empresa:* {nome}\n"
                f"📅 *Abertura:* {abertura}\n"
                f"🟢 *Situação:* {situacao}\n"
                f"💰 *Capital Social:* R$ {float(capital):,.2f}\n\n"
            )

            if situacao == "ACTIVE" or situacao == "ATIVA":
                resposta += "✅ *Filtro Inicial Aprovado!* Em breve enviarei a proposta de juros mínimos para você no chat."
            else:
                resposta += "⚠️ *Alerta:* Empresa consta como INATIVA. Análise pausada."

            return resposta
        else:
            return "❌ Erro temporário ao consultar dados do CNPJ."
    except Exception as e:
        return f"❌ Erro de conexão ao analisar o CNPJ: {e}"

def enviar_whatsapp(numero, texto):
    """ Função que conecta com a Z-API para disparar a mensagem de volta pro cliente """
    payload = {"phone": numero, "message": texto}
    headers = {"Content-Type": "application/json"}
    try:
        requests.post(Z_API_URL, json=payload, headers=headers, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar mensagem via WhatsApp: {e}")

@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    dados_recebidos = request.json
    print("\n📩 Nova mensagem recebida do WhatsApp:", dados_recebidos)

    texto_cliente = dados_recebidos.get("text", "").lower().strip()
    numero_cliente = dados_recebidos.get("phone", "")
    eh_grupo = dados_recebidos.get("isGroup", False)
    esta_salvo = dados_recebidos.get("isContact", False)

    # TRAVA 1: Se for grupo, ignora 100%
    if eh_grupo:
        return jsonify({"status": "Ignorado: Grupo"}), 200

    # SE ESTIVER SALVO NA AGENDA: O robô só responde se a pessoa pedir a consulta do CNPJ diretamente
    if esta_salvo:
        if "consult cnpj" in texto_cliente:
            apenas_numeros = "".join(filter(str.isdigit, texto_cliente))
            if len(apenas_numeros) == 14:
                resultado = consultar_cnpj(apenas_numeros)
                enviar_whatsapp(numero_cliente, resultado)
                return jsonify({"status": "CNPJ de contato salvo processado"}), 200
        return jsonify({"status": "Contato salvo mandando mensagem comum. Ignorado."}), 200

    # SE FOR UM CLIENTE NOVO (NÃO SALVO NA AGENDA):
    # Passo A: Se ele digitou o comando de consulta, o robô roda a análise
    if "consult cnpj" in texto_cliente:
        apenas_numeros = "".join(filter(str.isdigit, texto_cliente))
        if len(apenas_numeros) == 14:
            resultado = consultar_cnpj(apenas_numeros)
            enviar_whatsapp(numero_cliente, resultado)
            return jsonify({"status": "CNPJ de cliente novo processado"}), 200

    # Passo B: Se ele mandou qualquer outra mensagem (ex: Oi, Quero crédito, etc), manda o texto de Boas-Vindas oficial
    mensagem_boas_vindas = (
        "Olá! Seja muito bem-vindo(a). 👋\n"
        "Obrigado pelo contato. Aqui o atendimento é direto, sem burocracia bancária e focado em resolver a necessidade do seu caixa rápido.\n\n"
        "Para eu iniciar a sua análise de crédito imediata, por favor, me envie as seguintes informações básicas:\n"
        "1️⃣ Número do seu CNPJ:\n"
        "2️⃣ Valor que a sua empresa precisa hoje:\n"
        "3️⃣ Para quando você precisa desse recurso?\n\n"
        "Assim que você responder escrevendo *consult cnpj* seguido do seu número, meus modelos de dados vão rodar a análise e eu mesmo vou te dar o retorno por aqui em poucos minutos. Obrigado!"
    )
    
    enviar_whatsapp(numero_cliente, mensagem_boas_vindas)
    return jsonify({"status": "Mensagem de boas-vindas enviada para cliente novo"}), 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)
