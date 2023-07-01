from flask import Flask, request, jsonify
import json
import time
import sys
import socket 
from googletrans import Translator

class Fiberhome():
    
    @staticmethod
    def retornaResposta(resposta):
        '''Método que interpreta a resposta recebida e devolve a mensagem para ser enviada via json'''

        if "resource does not exist" in resposta:
            return "O dispositivo não existe"
        elif "the alarm does not exist" in resposta:
            return "O alarme não existe"
        elif "missing parameter" in resposta:
            return "Ausência de parâmetro"
        elif "invalid parameter format" in resposta:
            return "Formato de parâmetro inválido"
        elif "input parameter error" in resposta:
            return "Parâmetro de entrada inválido"
        elif "device may not support this operation" in resposta:
            return "O dispositivo pode não suportar esta operação"
        elif "device operation failed" in resposta:
            return "A operação no dispositivo falhou"
        elif "device is busy" in resposta:
            return "O dispositivo está ocupado"
        elif "EMS may not support this operation" in resposta:
            return "O EMS pode não suportar esta operação"
        elif "EMS operation failed" in resposta:
            return "Falha na operação do EMS"
        elif "EMS exception happens" in resposta:
            return "Aconteceu uma exceção no EMS"
        elif "user is busy" in resposta:
            return "O usuário está ocupado"
        elif "user is testing" in resposta:
            return "O usuário está em teste"
        elif "test module is busy" in resposta:
            return "O módulo de teste está ocupado"
        elif "resource already exist" in resposta:
            return "O nome ja existe"
        elif "No error" in resposta:
            return "Sucesso"
        else:
            return "Erro"
    
    def conexao(ip_servidor_tl1, porta_servidor_tl1, usuario_anm, senha_anm):
        '''Método que realiza a conexao via TL1'''

        global conexao
        #AF_INET informa que será usado o  procolo TCP
        #SOCK_STREAM informa que será usado IPV4 na conexão
        conexao = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conexao.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        tmp = conexao.connect_ex((ip_servidor_tl1, porta_servidor_tl1))
        #Usuário e senha do anm/unm
        script_conexao = 'LOGIN:::CTAG::UN='+usuario_anm+',PWD='+senha_anm+';'
        script_conexao = script_conexao.encode('utf-8')
        #script_handshake = 'SHAKEHAND:::CTAG::;'
        conexao.send(script_conexao)
        #conexao.sendall(script_handshake.encode('utf-8'))
        time.sleep(2)

    @staticmethod
    def logout():
        '''Método para encerrar sessão da conexão no servidor após envio do script'''

        script_logout = 'LOGOUT:::CTAG::;'
        script_logout = script_logout.encode('utf-8')
        conexao.send(script_logout)
        time.sleep(2)
        conexao.shutdown(1)
        time.sleep(2)
        conexao.close()

    def buscaOnu(ip_olt):
        '''Método para buscar ONU's não autorizadas e retornar os de SLOT, PON, IP da OLT e Tipo da ONU'''

        #Recebe as informações em json de conexão via POST
        #cria os arrays para receber as informações da ONUs
        resposta = [] 
        #ip da OLT recebido via POST
        oltip = ip_olt
        #Padrão para buscar em todas as PONs
        script_busca_onu = 'LST-UNREGONU::OLTID='+oltip+':CTAG::;'
        #script_busca_onu = script_busca_onu.encode('utf-8')
        #Envia os dados via sandall, metodo do socket, todo codificado em uma cadeia de strings em UTF-8
        conexao.settimeout(15)
        conexao.sendall(script_busca_onu.encode('utf-8'))
        time.sleep(2)
        #Recebe os dados retornado
        data = conexao.recv(5000)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        data = data.replace(" ","")
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        for linha in data.split("\n"):
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            #separada cada elementos da linha colocando como elemento de uma lista
            elementos = linha.split(" ")
            #Caso a quantidade de elementos seja maior que 7, é a linha que contem as informações da(s) onu(s)
            if len(elementos) > 7 and not(elementos[0] == "SLOTNO"):
                dados_onu = {
                    "SLOT": elementos[0],
                    "PON": elementos[1],
                    "MAC": elementos[2][0:12],
                    "TIPO_ONU": elementos[7]
                }
                #insere o conjunto dentro do array de resposta
                #Dessa forma, caso tenha mais de uma ONU, todas serão enviadas via json
                resposta.append(dados_onu)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)  
        Fiberhome.logout()
        return data_json

    def autorizaOnu(ip_olt, slot_pon, mac_onu, tipo_onu, nome_cliente, vlan, tipo_conexao, usuario_pppoe, pass_pppoe='101010'):
        '''Método para realizar a liberação da ONU. Retorna JSON com mensagem de Sucesso ou Erro
        OBS. O script para tipo_onu = ONU Mini, pode ser utilizado para ONU's de outras marcas como Intelbras, Huawei, etc.'''
        resposta = []
        
        #Exceções para os tipos de ONU, variando a forma de liberar a ONU de acordo com a necessidade de fábrica ou preferência pessoal.
        if tipo_conexao == 'Bridge' and tipo_onu == 'ONU Mini':
            tipo_onu = 'AN5506-01-A1'
            script_liberacao_onu = f"""
            ADD-ONU::OLTID={ip_olt},PONID=NA-NA-{slot_pon}:CTAG::AUTHTYPE=MAC,
            ONUID={mac_onu},NAME={usuario_pppoe} - {nome_cliente},ONUTYPE={tipo_onu};
            CFG-LANPORTVLAN::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu},ONUPORT=NA-NA-NA-1:CTAG::CVLAN={vlan},CCOS=0;"""

        elif tipo_conexao == 'Router' and tipo_onu != 'AN5506-04-FA' and tipo_onu != 'AN5506-02-F':
            script_liberacao_onu = f"""
            ADD-ONU::OLTID={ip_olt},PONID=NA-NA-{slot_pon}:CTAG::AUTHTYPE=MAC,
            ONUID={mac_onu},NAME={usuario_pppoe} - {nome_cliente},ONUTYPE={tipo_onu};
            SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu}:CTAG::STATUS=2;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,
            MODE=2,CONNTYPE=2,COS=0,VLAN={vlan},QOS=2,NAT=1,IPMODE=3,PPPOEPROXY=2,
            PPPOEUSER={usuario_pppoe},PPPOEPASSWD={pass_pppoe},PPPOENAME=interface1,
            PPPOEMODE=1,QINQSTATE=0,UPORT=0;"""

        elif tipo_onu == 'AN5506-04-FA':
            script_liberacao_onu = f"""
            ADD-ONU::OLTID={ip_olt},PONID=NA-NA-{slot_pon}:CTAG::
            AUTHTYPE=MAC,ONUID={mac_onu},NAME={usuario_pppoe} - {nome_cliente},
            ONUTYPE={tipo_onu};SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
            ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=2;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,MODE=2,
            CONNTYPE=2,COS=0,VLAN={vlan},QOS=2,NAT=1,IPMODE=3,PPPOEPROXY=2,
            PPPOEUSER={usuario_pppoe},PPPOEPASSWD={pass_pppoe},PPPOENAME=interface1,
            PPPOEMODE=1,QINQSTATE=0,UPORT=0;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,MODE=2,
            CONNTYPE=2,COS=0,VLAN={vlan},QOS=2,NAT=1,IPMODE=3,PPPOEPROXY=2,
            PPPOEUSER={usuario_pppoe},PPPOEPASSWD={pass_pppoe},PPPOENAME=interface1,
            PPPOEMODE=1,QINQSTATE=0,SSID=1;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,MODE=2,
            CONNTYPE=2,COS=0,VLAN={vlan},QOS=2,NAT=1,IPMODE=3,PPPOEPROXY=2,
            PPPOEUSER={usuario_pppoe},PPPOEPASSWD={pass_pppoe},PPPOENAME=interface1,
            PPPOEMODE=1,QINQSTATE=0,SSID=5;"""

        elif tipo_onu == 'AN5506-02-F':
            script_liberacao_onu = f"""
            ADD-ONU::OLTID={ip_olt},PONID=NA-NA-{slot_pon}:CTAG::
            AUTHTYPE=MAC,ONUID={mac_onu},NAME={usuario_pppoe} - {nome_cliente},
            ONUTYPE={tipo_onu};SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::
            STATUS=2;SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
            ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,MODE=2,CONNTYPE=2,COS=0,
            VLAN={vlan},QOS=2,NAT=1,IPMODE=3,PPPOEPROXY=2,PPPOEUSER={usuario_pppoe},
            PPPOEPASSWD={pass_pppoe},PPPOENAME=interface1,PPPOEMODE=1,QINQSTATE=0,
            UPORT=0;SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu}:CTAG::STATUS=1,MODE=2,CONNTYPE=2,COS=0,VLAN={vlan},QOS=2,
            NAT=1,IPMODE=3,PPPOEPROXY=2,PPPOEUSER={usuario_pppoe},PPPOEPASSWD={pass_pppoe},
            PPPOENAME=interface1,PPPOEMODE=1,QINQSTATE=0,SSID=1;"""

        elif tipo_conexao == 'Bridge' and tipo_onu != 'ONU Mini':
            script_liberacao_onu = f"""
            ADD-ONU::OLTID={ip_olt},PONID=NA-NA-{slot_pon}:CTAG::
            AUTHTYPE=MAC,ONUID={mac_onu},NAME={usuario_pppoe} - {nome_cliente},
            ONUTYPE={tipo_onu};SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
            ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=2;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,MODE=2,
            CONNTYPE=1,COS=0,VLAN={vlan},QOS=2,NAT=1,QINQSTATE=0,UPORT=0;"""
            
        #script_liberacao_onu = script_liberacao_onu.encode('utf-8')
        #Envia os dados via sendall, metodo do socket, todo codificado em uma cadeia de strings em UTF-8
        conexao.settimeout(15)
        conexao.sendall(script_liberacao_onu.encode('utf-8'))
        time.sleep(2)
        #Recebe os dados retornado
        data = conexao.recv(1024)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        
        #data = data.replace(" ","")
        for linha in data.split("\n"):
            #identifica dentro da linha, qual contem a resposta da requisição (ENDESC)
            if "ENDESC" in linha:
                #Quebra o conteudo da linha e faz com que cada parte separada por igual seja um elemento da lista
                elemento = linha.split("=")
                resp = Fiberhome.retornaResposta(elemento[2])
                break
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        mensagem = {
            "Request": resp
        }  
        resposta.append(mensagem)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)  
        Fiberhome.logout()
        return data_json

    def desautorizaOnu(ip_olt, mac_onu, slot_pon):
        '''Método para realizar desautorização da ONU. Retorna JSON com mensagem de Sucesso ou Erro'''

        resposta = [] 
        script_exclusao_onu = 'DEL-ONU::OLTID='+ip_olt+',PONID=NA-NA-'+slot_pon+':CTAG::ONUIDTYPE=MAC,ONUID='+mac_onu+';'
        #script_exclusao_onu = script_exclusao_onu.encode('utf-8')
        #Envia os dados via sendall, metodo do socket, todo codificado em uma cadeia de strings em UTF-8
        conexao.settimeout(15)
        conexao.sendall(script_exclusao_onu.encode('utf-8'))
        time.sleep(2)
        #Recebe os dados retornado
        data = conexao.recv(1024)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        for linha in data.split("\n"):
            #identifica dentro da linha, qual contem a resposta da requisição (ENDESC)
            if "ENDESC" in linha:
                #Quebra o conteudo da linha e faz com que cada parte separada por igual(=) seja um elemento da lista
                elemento = linha.split("=")
                #a posição 2 da lista de elementos é a resposta
                #a resposta é passada para a função retornaResposta, que verifica a mensagem, e retorna a resposta que será enviada no json
                resp = Fiberhome.retornaResposta(elemento[2])
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        mensagem = {
            "msg": resp
        }
        resposta.append(mensagem)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)  
        Fiberhome.logout()
        return data_json

    def consultaSinalOnu(ip_olt, mac_onu, slot_pon):
        '''Retorna dB (Sinal) da ONU. Caso queira realizar a requisição de mais informações 
        junto com o dB, utilize o método consultainformações'''

        resposta = []
        script_consulta_sinal_onu = 'LST-OMDDM::OLTID='+ip_olt+',PONID=NA-NA-'+slot_pon+',ONUIDTYPE=MAC,ONUID='+mac_onu+':CTAG::;'
        #script_consulta_sinal_onu = script_consulta_sinal_onu.encode('utf-8')
        #Envia os dados via sendall, metodo do socket, todo codificado em uma cadeia de strings em UTF-8
        conexao.settimeout(15)
        conexao.sendall(script_consulta_sinal_onu.encode('utf-8'))
        time.sleep(2)
        #Recebe os dados retornado
        data = conexao.recv(1024)
        #decodifica data = conexao.recv(1024) esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        for linha in data.split("\n"):
            #identifica dentro da linha, qual contem a resposta da requisição (ENDESC)
            if "IRNE" in linha:
                #Quebra o conteudo da linha e faz com que cada parte separada por igual(=) seja um elemento da lista
                elemento = linha.split("=")
                #a posição 2 da lista de elementos é a resposta
                #a resposta é passa para a função retornaResposta, que verifica a mensagem e retorna a resposta que será enviada no json
                resp = Fiberhome.retornaResposta(elemento[2])
                mensagem = {
                    "msg": resp
                }
                resposta.append(mensagem)
        data = data.replace(" ","")
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        for linha in data.split("\n"):
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            #separada cada elementos da linha colocando como elemento de uma lista
            elementos = linha.split(" ")
            #Caso a quantidade de elementos seja maior que 7, é a linha que contem as informações da onu
            if len(elementos) > 7 and not(elementos[0] == "ONUID"):
                dados_onu = {
                    "SINAL": elementos[1]
                }
                #insere o conjunto dentro do array de resposta
                #Dessa forma, caso tenha mais de uma ONU, todas serão enviadas via json
                resposta.append(dados_onu)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)
        Fiberhome.logout()
        return data_json

    def configuraWiFi(ip_olt, mac_onu, slot_pon, ssid_name, preshared_key, tipo_onu):
        '''Configura Wi-Fi de ONU's 04-FA ou 02-F. 
        Retorna mensagem de sucesso da Rede 2.4 e 5GHz em caso de ONU 04-FA'''

        resposta = []
        resp = []

        #Configuração do Wi-Fi 2,4 E 5.0
        if tipo_onu == 'AN5506-04-FA':
            script_configura_wifi = f"""
            MODIFY-WIFISERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu}:CTAG::ENABLE=enable,WILESS-AREA=5,WILESS-CHANNEL=0,
            WILESS-STANDARD=802.11bgn,WORKING-FREQUENCY=2.4GHZ,T-POWER=100,SSID=1,
            SSID-ENABLE=1,SSID-NAME={ssid_name},SSID-VISIBALE=0,AUTH-MODE=WPA2PSK,
            ENCRYP-TYPE=AES,FREQUENCY-BANDWIDTH=20/40MHZ,PRESHARED-KEY={preshared_key};
            CFG-WIFISERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu}:CTAG::ENABLE=enable,WILESS-AREA=5,WILESS-CHANNEL=0,
            WILESS-STANDARD=802.11ac,WORKING-FREQUENCY=5.8GHZ,T-POWER=100,SSID=1,
            SSID-ENABLE=1,SSID-NAME={ssid_name}_5G,SSID-VISIBALE=0,AUTH-MODE=WPA2PSK,
            ENCRYP-TYPE=AES,FREQUENCY-BANDWIDTH=80MHZ,PRESHARED-KEY={preshared_key};"""

        elif tipo_onu == 'AN5506-02-F':
            script_configura_wifi = f"""
            MODIFY-WIFISERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
            ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::ENABLE=enable,WILESS-AREA=5,
            WILESS-CHANNEL=0,WILESS-STANDARD=802.11bgn,WORKING-FREQUENCY=2.4GHZ,
            T-POWER=100,SSID=1,SSID-ENABLE=1,SSID-NAME={ssid_name},SSID-VISIBALE=0,
            AUTH-MODE=WPA2PSK,ENCRYP-TYPE=AES,FREQUENCY-BANDWIDTH=20/40MHZ,
            PRESHARED-KEY={preshared_key};"""

        conexao.settimeout(15)
        conexao.sendall(script_configura_wifi.encode('utf-8'))
        time.sleep(5)


        #Recebe os dados retornado
        data = conexao.recv(1024)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        for linha in data.split("\n"):
            #identifica dentro da linha, qual contem a resposta da requisição (ENDESC)
            if "ENDESC" in linha:
                #Quebra o conteudo da linha e faz com que cada parte separada por igual(=) seja um elemento da lista
                elemento = linha.split("=")
                #a posição 2 da lista de elementos é a resposta
                #a resposta é passada para a função retornaResposta, que verifica a mensagem e retorna a resposta que será enviada no json
                resp.append(Fiberhome.retornaResposta(elemento[2]))
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        if tipo_onu == 'AN5506-04-FA':
            mensagem = {
                "Wi-Fi 2.4": resp[0],
                "Wi-Fi 5.0": resp[1]
            }
        elif tipo_onu == 'AN5506-02-F':
            mensagem = {
                "Wi-Fi 2.4": resp[0]
            }
        resposta.append(mensagem)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)
        Fiberhome.logout()
        return data_json


    def obter_slot_pon(mac_onu):
        '''Método para retornar o SLOT, PON, Nome da OLT, Nome da ONU e Tipo da ONU utilizando o MAC de uma ONU'''
        resposta = []
        nomeonu = ''
        script_obter_slot_pon = 'QUERY-ONUINFO::ONUTYPE=MAC,ONUID='+mac_onu+':CTAG::;'

        conexao.settimeout(15)
        conexao.sendall(script_obter_slot_pon.encode('utf-8'))
        time.sleep(2)

        data = conexao.recv(5000)
        data = data.decode("utf-8")
        

        for linha in data.split("\n"):
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            #separa cada elementos da linha colocando como elemento de uma lista
            #linha = linha.replace("-","")
            elementos = linha.split(" ")
            
            if len(elementos) >= 10 and not elementos[0] == 'System':

                for elemento in elementos:
                    try:
                        if elemento[:6] == 'AN5506':
                            break
                        elif elemento == elementos[1]:
                            nomeonu = elemento
                        elif elemento != elementos[0]:
                            nomeonu = nomeonu+" "+elemento
                    except:
                        if elemento == elementos[1]:
                            nomeonu = elemento
                        elif elemento != elementos[0]:
                            nomeonu = nomeonu+" "+elemento
                        
        data = data.replace(" ","")

        for linha in data.split("\n"):
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            #separada cada elementos da linha colocando como elemento de uma lista
            #linha = linha.replace("-","")
            elementos = linha.split(" ")
            if len(elementos) == 10 and not(elementos[0] == 'System'):
                if len(nomeonu.split('-')) > 1:
                    nomeonu = nomeonu.split('-')
                    nomeonu = nomeonu[0]+'-'+nomeonu[1]
                else:
                    nomeonu = nomeonu
                    
                slot_pon = {
                    "OLT": elementos[0],
                    "Nome ONU": nomeonu,
                    "Tipo ONU": elementos[2],
                    "SLOT": elementos[3],
                    "PON": elementos[4]
                }
                resposta.append(slot_pon)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)  
        Fiberhome.logout()
        return data_json
        
        
    def buscatodasOnus():
        '''Método para buscar todas ONU's pedindo liberação em seu UNM/ANM. 
        Retorna IP da OLT, SLOT, PON, MAC da ONU e Tipo da ONU'''

        #Recebe as informações em json de conexão via POST
        #cria os arrays para receber as informações da ONUs
        resposta = [] 
        #Padrão para buscar em todas as PONs
        script_busca_onu = 'LST-UNREGONU:::CTAG::;'
        #script_busca_onu = script_busca_onu.encode('utf-8')
        #Envia os dados via sandall, metodo do socket, todo codificado em uma cadeia de strings em UTF-8
        conexao.settimeout(15)
        conexao.sendall(script_busca_onu.encode('utf-8'))
        time.sleep(6)
        #Recebe os dados retornado
        data = conexao.recv(5000)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        data = data.replace(" ","")
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        for linha in data.split("\n"):
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            #separada cada elementos da linha colocando como elemento de uma lista
            elementos = linha.split(" ")
            #Caso a quantidade de elementos seja maior que 7, é a linha que contem as informações da(s) onu(s)
            if len(elementos) > 8 and not(elementos[0] == "OLTID"):
                
                dados_onu = {
                    "OLTID": elementos[0],
                    "SLOT": elementos[1],
                    "PON": elementos[2],
                    "MAC": elementos[3][0:12],
                    "TIPO_ONU": elementos[8]
                }
                #insere o conjunto dentro do array de resposta
                #Dessa forma, caso tenha mais de uma ONU, todas serão enviadas via json
                resposta.append(dados_onu)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)  
        Fiberhome.logout()
        return data_json  


    def configurawifipadrao(ip_olt,mac_onu,slot_pon,tipo_onu):
        '''Configura Wi-Fi com nome de rede com nome definido na variável redepadrao e senha na variável senhapadrao.
        Retorna JSON com mensagem de Sucesso ou Erro para as redes 2.4 e 5GHz em caso de ONU 04-FA'''

        resposta = []
        resp = []
        redepadrao = 'Rede Padrao'
        senhapadrao = '999999999'

        if tipo_onu == 'AN5506-04-FA':
            scriptconfigurawifi = f"""
            MODIFY-WIFISERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
            ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::ENABLE=enable,WILESS-AREA=5,
            WILESSCHANNEL=0,WILESS-STANDARD=802.11bgn,WORKING-FREQUENCY=2.4GHZ,
            TPOWER=100,SSID=1,SSID-ENABLE=1,SSID-NAME={redepadrao},SSIDVISIBALE=0,
            AUTH-MODE=WPA2PSK,ENCRYP-TYPE=AES,FREQUENCY-BANDWIDTH=20/40MHZ,
            PRESHARED-KEY={senhapadrao};MODIFY-WIFISERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::ENABLE=enable,
            WILESS-AREA=5,WILESSCHANNEL=0,WILESS-STANDARD=802.11ac,WORKING-FREQUENCY=5.8GHZ,
            TPOWER=100,SSID=1,SSID-ENABLE=1,SSID-NAME={redepadrao}_5G,SSIDVISIBALE=0,
            AUTH-MODE=WPA2PSK,ENCRYP-TYPE=AES,FREQUENCY-BANDWIDTH=80MHZ,PRESHARED-KEY={senhapadrao};"""

        elif tipo_onu == 'AN5506-02-F':
            scriptconfigurawifi = f"""
            MODIFY-WIFISERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
            ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::ENABLE=enable,WILESS-AREA=5,
            WILESSCHANNEL=0,WILESS-STANDARD=802.11bgn,WORKING-FREQUENCY=2.4GHZ,
            TPOWER=100,SSID=1,SSID-ENABLE=1,SSID-NAME={redepadrao},SSIDVISIBALE=0,
            AUTH-MODE=WPA2PSK,ENCRYP-TYPE=AES,FREQUENCY-BANDWIDTH=20/40MHZ,PRESHARED-KEY={senhapadrao};"""

        conexao.settimeout(15)
        conexao.sendall(scriptconfigurawifi.encode('utf-8'))
        time.sleep(5)

        #Recebe os dados retornado
        data = conexao.recv(1024)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode("utf-8")
        for linha in data.split("\n"):
            #identifica dentro da linha, qual contem a resposta da requisição (ENDESC)
            if "ENDESC" in linha:
                #Quebra o conteudo da linha e faz com que cada parte separada por igual(=) seja um elemento da lista
                elemento = linha.split("=")
                #a posição 2 da lista de elementos é a resposta
                #a resposta é passa para a função retornaResposta, que verifica a mensagem, e retorna a resposta que será enviada no json
                resp.append(Fiberhome.retornaResposta(elemento[2]))
        #Percorre todas linhas de retorno, separando cada uma delas como elementos de uma lista onde existe quebra de linha
        if tipo_onu == 'AN5506-04-FA':
            mensagem = {
                "msg": "Wi-Fi 2.4 "+resp[0]+" / Wi-Fi 5.0 "+resp[1]+""
            }
        elif tipo_onu == 'AN5506-02-F':
            mensagem = {
                "msg": "Wi-Fi 2.4 "+resp[0]
            }
        resposta.append(mensagem)
        #Convertendo um dicionário criado em um json
        data_json = json.dumps(resposta)
        Fiberhome.logout()
        return data_json

    def alarme(ip_olt,slot_pon,mac_onu):
        '''Método sendo desenvolvido onde retorna o alarme de uma determinada ONU.
        Não finalizado pois o TL1 não retorna as informações de forma coesa.'''

        #EM TESTE --------------------
        resposta = []
        resp = []
        scriptconsulta = 'QUERY-ALARM::OLTID='+ip_olt+',PONID=NA-NA-'+slot_pon+',ONUIDTYPE=MAC,ONUID='+mac_onu+':CTAG::;'

        conexao.settimeout(15)
        conexao.sendall(scriptconsulta.encode('utf-8'))

        time.sleep(2)

        data = conexao.recv(1024)
        #decodifica esses dados de bytes para uma cadeia de strings UTF-8
        data = data.decode('gb2312')
        translator = Translator()
        data = translator.translate(data)
        data = data.text

        for linha in data.split("\n"):
            
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            
            #separada cada elementos da linha colocando como elemento de uma lista
            
            elemento = linha.split(" ")
            
            if len(elemento) > 16 and not elemento[0] == 'SERIALID':
                for i in elemento:
                    try:
                        if i[0] == '-' and i[3] == '-':
                            dataat = dataat+i
                            resp.append(dataat)
                    except:
                        pass
                    try:
                        if i[4] == '-' and i[7] == '-':
                            dataat = i
                    except:
                        pass
                    try:
                        if len(i) == 5 and i[2] == '-':
                            dataat = dataat + i
                            resp.append(dataat)
                    except:
                        pass
                    try:
                        if len(i) == 2:
                            if type(int(i)):
                                dataat = dataat+i
                                resp.append(dataat)
                    except:
                        pass
                    
                    if i == '310005' or i == '110008':
                        resp.append(i)

                    elif len(i.replace('-','')) == 8 and i[4] == '-':
                        resp.append(i)
                    
                    elif i == '2022' or i == '2022-':
                            dataat = i

                    elif len(i.replace(':','')) == 6 and i[2] == ':' and i[5] == ':':
                        resp.append(i)

                    elif i == 'ENDESC=the':
                        resp.append('Sem Alarmes')
        print(resp)
        pass

    def consultainformacoes(ip_olt,mac_onu,slot_pon):
        '''Método para consulta de informações de uma determinada ONU.
        Retorna JSON com dB, Modo ONU (Bridge ou Router) e IP WAN em caso de ONU em modo Router'''

        resposta = []
        modoonu = ''
        ipwan = 'N/A'
        #Script TL1 que fará a busca das informações da ONU dentro da OLT
        script_consultas = f"""
        LST-OMDDM::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
        ONUID={mac_onu}:CTAG::;LST-PORTVLAN::OLTID={ip_olt},PONID=NA-NA-{slot_pon},
        ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::;LST-ONUWANSERVICECFG::OLTID={ip_olt},
        PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::;"""

        conexao.settimeout(30)
        conexao.sendall(script_consultas.encode('utf-8'))
        time.sleep(12)

        data = conexao.recv(5000)
        data = data.decode("utf-8")

        #Os dados retornados são iterados para obtermos as informações separadas
        for linha in data.split("\n"):
            if "ENDESC" in linha:
                linha = linha.replace('\r','')
                elemento = linha.split('=')
                #Caso a ONU não esteja liberada, retorna dB como N/A
                if elemento[-1] == 'ONU not registered':
                    db = {
                        'dB': 'N/A'
                    }
                    resposta.append(db)

        data = data.replace(' ','')

        #Nova iteração agora para retorno do dB, Modo e IP
        for linha in data.split("\n"):
            linha = linha.replace("\t"," ")
            linha = linha.replace("\r","")
            
            elementos = linha.split(" ")
            
            if len(elementos) == 13 and not elementos[0] == 'ONUID':
                db = {
                    'dB': elementos[1]
                }
                resposta.append(db)

            if len(elementos) == 10 and not elementos[0] == 'ONUIP':
                modoonu = {
                    'Modo ONU': 'Bridge',
                    'IP Wan': ipwan
                }
                resposta.append(modoonu)
            
            
            elif len(elementos) >= 21 and not elementos[0] == 'SVCNAME':
                if elementos[2] == 'route':
                    modo = 'Router'
                    ipwan = elementos[7]
                elif elementos[2] == 'bridge':
                    modo = 'Bridge'
                modoonu = {
                    'Modo ONU': modo,
                    'IP Wan': ipwan
                }
                resposta.append(modoonu)
            

        if modoonu == '':
            modoonu = {
                        'Modo ONU': 'INFORMAÇÃO NÃO IDENTIFICADA',
                        'IP Wan': ipwan
                    }
            resposta.append(modoonu)
        data_json = json.dumps(resposta)
        Fiberhome.logout()
        return data_json

    def alterarmodoonu(ip_olt,mac_onu,slot_pon,vlan,login,senha,modoantigo):
        '''Altera o modo de conexão da ONU sendo bridge para router ou vice-versa
        Retorna JSON com mensagem de Sucesso ou Erro'''
        
        resposta = []
            
        #Modo utilizado para alterar o tipo de conexão que a ONU fará. Disponível para ONU's 04-FA, 02-F, 02-B e 01-A1
        if modoantigo == 'route':
            scriptalteramodo = f"""
            SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu}':CTAG::STATUS=2;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,
            MODE=2,CONNTYPE=1,VLAN={vlan},COS=0,UPORT=0;"""

        elif modoantigo == 'bridge':
            scriptalteramodo = f"""
            SET-WANSERVICE::OLTID={ip_olt},PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,
            ONUID={mac_onu}:CTAG::STATUS=2;SET-WANSERVICE::OLTID={ip_olt},
            PONID=NA-NA-{slot_pon},ONUIDTYPE=MAC,ONUID={mac_onu}:CTAG::STATUS=1,
            MODE=2,CONNTYPE=2,COS=0,VLAN={vlan},QOS=2,NAT=1,IPMODE=3,PPPOEPROXY=2,
            PPPOEUSER={login},PPPOEPASSWD={senha},PPPOENAME=interface1,PPPOEMODE=1,
            QINQSTATE=0,UPORT=0;"""

        conexao.settimeout(15)
        conexao.sendall(scriptalteramodo.encode('utf-8'))
        time.sleep(5)
        
        data = conexao.recv(1024)
        data = data.decode('utf-8')
        
        #Iteração dos dados retornados no TL1
        for linha in data.split('\n'):
            if 'ENDESC' in linha:
                elementos = linha.split('=')
                respret = Fiberhome.retornaResposta(elementos[2])

                msg = {
                    'mensagem': respret
                }

                resposta.append(msg)
        data_json = json.dumps(resposta)
        Fiberhome.logout()
        return data_json
            

        