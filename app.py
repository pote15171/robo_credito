import requests
from flask import Flask, jsonify, request

app = Flask(__name__)


# Função que consulta o CNPJ na base de dados pública da Receita WS
def consultar_cnpj(cnpj):
    cnpj_limpo = "".join(filter(str.isdigit, cnpj))
    url = f"https://receitaws.com.br{cnpj_limpo}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            dados = response.json()
            if dados.get("status") == "ERROR":
                return "❌ CNPJ inválido ou não encontrado na base de dados."

            nome = dados.get("nome")
            abertura = dados.get("abertura")
            situacao = dados.get("situacao")
            capital = dados.get("capital_social", "0.00")

            # Montando o texto da mensagem que vai pro cliente
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


# Rota (Webhook) que vai escutar as mensagens do WhatsApp
@app.route("/webhook", methods=["POST"])
def receber_mensagem():
    dados_recebidos = request.json
    print("\n📩 Nova mensagem recebida do WhatsApp:", dados_recebidos)

    # Pegamos as informações de quem enviou e o tipo de chat
    texto_cliente = dados_recebidos.get("text", "").lower().strip()
    numero_cliente = dados_recebidos.get("phone", "")
    eh_grupo = dados_recebidos.get("isGroup", False)

    # TRAVA 1: Se a mensagem vier de qualquer GRUPO, o robô ignora na hora
    if eh_grupo:
        return jsonify({"status": "Ignorado: Mensagem vinda de um grupo."}), 200

    # TRAVA 2: Só responde se a mensagem contiver o comando "consult cnpj"
    # Funciona para qualquer um: contatos novos ou contatos salvos da sua agenda!
    if "consult cnpj" in texto_cliente:
        # Extrai apenas os números da mensagem para ver se tem os 14 dígitos do CNPJ
        apenas_numeros = "".join(filter(str.isdigit, texto_cliente))

        if len(apenas_numeros) == 14:
            print(f"⚙️ Comando correto e CNPJ detectado: {apenas_numeros}")
            resultado_analise = consultar_cnpj(apenas_numeros)
            print(f"📢 Resposta preparada para {numero_cliente}:\n{resultado_analise}")
            
            # Nas próximas etapas, colocaremos a linha de envio para o WhatsApp aqui
            return jsonify({"status": "CNPJ processado"}), 200
        else:
            print("⚠️ Comando digitado correto, mas falta o número do CNPJ.")
            return jsonify({"status": "Aguardando CNPJ válido"}), 200

    # Se a pessoa mandar um "Oi", "Tudo bem?" ou qualquer mensagem comum, o robô ignora em silêncio
    return jsonify({"status": "Mensagem ignorada: Não usou o comando correto."}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)