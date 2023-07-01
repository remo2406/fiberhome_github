from flask import Flask, request, jsonify
import json
import time
import sys
import socket 
import os
from gevent.pywsgi import WSGIServer
#modulo que executa a conexão via ssh

#importa a classe com os métodos da Fiberhome
from Fiberhome import Fiberhome

app = Flask(__name__)

#Método para realizar teste do servidor
@app.route("/", methods=["GET"])
def hello():
    return "<h1 style='color:purple'>Teste de Utilização</h1>"

#Método que busca as ONUs não autorizadas em determinada OLT
@app.route("/buscaOnu", methods=['POST'])
def buscaOnu():
    #Recebe as informações em json de conexão via POST
    dados_olt = request.json
    
    #utiliza o método de conexão Fiberhome, passando os dados recebidos via post
    Fiberhome.conexao(dados_olt['ip_servidor_tl1'], int(dados_olt['porta_servidor_tl1']), dados_olt['usuario_anm'], dados_olt['senha_anm'])
    #retorna as onus não autorizadas
    return Fiberhome.buscaOnu(dados_olt['ip_olt'])

#Método que busca as ONUs não autorizadas em todo UNM/ANM
@app.route("/buscatodasOnus", methods=['POST'])
def buscatodasOnus():
    #Recebe as informações em json de conexão via POST
    dados_olt = request.json
    #utiliza o método de conexão Fiberhome, passando os dados recebidos via post
    Fiberhome.conexao(dados_olt['ip_servidor_tl1'], int(dados_olt['porta_servidor_tl1']), dados_olt['usuario_anm'], dados_olt['senha_anm'])
    #retorna as onus não autorizadas
    return Fiberhome.buscatodasOnus()
    
#Método que realiza autorização das ONUs
@app.route("/autorizaOnu", methods=['POST'])
def autorizaOnu():
    #Recebe as informações em json de conexão via POST
    dados = request.json
    
    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    #utiliza o método de autorização Fiberhome, passando os dados recebidos via post
    return Fiberhome.autorizaOnu(dados['ip_olt'],dados['slot_pon'],dados['mac_onu'],dados['tipo_onu'],dados['nome_cliente'],dados['vlan'],dados['tipo_conexao'],dados['usuario_pppoe'],dados['pass_pppoe'])

#Método que realiza a desautorização das ONUs
@app.route("/desautorizaOnu", methods=['POST'])
def desautorizaOnu():
    #Recebe as informações em json de conexão via POST
    dados = request.json

    #utiliza o método de conexão Fiberhome, passando os dados recebidos via post
    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.desautorizaOnu(dados['ip_olt'],dados['mac_onu'],dados['slot_pon'])
    
#Método que realiza a consulta do Sinal da ONU
@app.route("/consultaSinalOnu", methods=['POST'])
def consultaSinalOnu():
    #Recebe as informações em json de conexão via POST
    dados = request.json
    
    #utiliza o método de conexão Fiberhome, passando os dados recebidos via post
    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.consultaSinalOnu(dados['ip_olt'],dados['mac_onu'],dados['slot_pon'])
    
#Método que configura Wi-Fi das ONUs
@app.route("/configuraWiFi", methods=['POST'])
def configuraWiFi():
    #Recebe as informações em json de conexão via POST
    dados = request.json
    #Recebe os dados do modulo Fiberhome e efetiva a alteração via POST
    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.configuraWiFi(dados['ip_olt'], dados['mac_onu'], dados['slot_pon'], dados['ssid_name'], dados['preshared_key'], dados['tipo_onu'])

#Método para Obter SLOT, PON, Nome da OLT e Tipo da ONU
@app.route('/obterslotpon', methods=['POST'])
def obterslotpon():
    #Recebe as informações em json de conexão via POST
    dados = request.json
    #Recebe os dados do modulo Fiberhome e efetiva a alteração via POST
    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.obter_slot_pon(dados['mac_onu'])

#Método para configurar ONU com Wi-Fi Padrão, sem definir através da Requisição
@app.route('/configurawifipadrao', methods=['POST'])
def configurawifipadrao():

    dados = request.json

    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.configurawifipadrao(dados['ip_olt'],dados['mac_onu'],dados['slot_pon'],dados['tipo_onu'])

#Método para consultar informações de uma ONU
@app.route('/consultainformacoes', methods=['POST'])
def consultainformacoes():

    dados = request.json

    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.consultainformacoes(dados['ip_olt'],dados['mac_onu'],dados['slot_pon'])

#Método para alterar tipo de conexão da ONU (Bridge para Router ou vice-versa)
@app.route('/alterarmodoonu', methods=['POST'])
def alterarmodoonu():

    dados = request.json

    Fiberhome.conexao(dados['ip_servidor_tl1'], int(dados['porta_servidor_tl1']), dados['usuario_anm'], dados['senha_anm'])
    return Fiberhome.alterarmodoonu(dados['ip_olt'],dados['mac_onu'],dados['slot_pon'],dados['vlan'],dados['login'],dados['senha'],dados['modoantigo'])



if __name__ == "__main__":
    #Para testes utilizamos um servidor local com o "run" do Flask. Caso tenha interesse em utilizar em servidor,
    #utilizar a biblioteca WSGIServer
    port = int(os.getenv("PORT", 5000))
    #http_server = WSGIServer(('', port), app)
    #http_server.serve_forever()
    app.run(host='0.0.0.0', port=port)
