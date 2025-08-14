from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import tempfile
import pandas as pd

app = Flask(__name__)
CORS(app)@app.route('/processos', methods=['GET'])
def get_processos():
    """Retorna os registros formatados conforme requisitado"""
    start = request.args.get('start', type=int)
    end = request.args.get('end', type=int)
    
    dados = carregar_dados()
    if not dados:
        return jsonify({"erro": "Nenhum dado disponível"}), 404
    
    if start is not None:
        dados = [p for p in dados if p.get("timestamp") and int(p["timestamp"]) >= start]
    if end is not None:
        dados = [p for p in dados if p.get("timestamp") and int(p["timestamp"]) <= end]
    
    return jsonify(dados), 200

UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db_path = os.path.join(os.getcwd(), "live.sqlite")


def carregar_dados():
    global db_path
    
    if not db_path or not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabelas_disponiveis = [t[0] for t in cursor.fetchall()]
        print("Tabelas disponíveis:", tabelas_disponiveis)
        
        tabelas = [t for t in ["processes1", "processes2", "processes3"] if t in tabelas_disponiveis]
        resultados = []
        
        for tabela in tabelas:
            try:
                cursor.execute(f"SELECT rowid, PackageName, Pids, Metrics FROM {tabela}")
                dados = cursor.fetchall()
                
                for row in dados:
                    try:
                        uid = row[0]  
                        package_name = row[1]
                        pids = row[2]
                        
                        metrics = row[3].split(':')
                        if len(metrics) >= 6:
                            metric_data = {
                                'timestamp': metrics[0],
                                'usagetime': metrics[1],
                                'delta_cpu_time': metrics[2],
                                'cpu_usage': metrics[3],
                                'rx_data': metrics[4],
                                'tx_data': metrics[5]
                            }
                        else:
                            metric_data = {
                                'timestamp': '',
                                'usagetime': '',
                                'delta_cpu_time': '',
                                'cpu_usage': '',
                                'rx_data': '',
                                'tx_data': ''
                            }
                        
                        registro = {
                            'timestamp': metric_data['timestamp'],
                            'uid': uid,
                            'package_name': package_name,
                            'delta_cpu_time': metric_data['delta_cpu_time'],
                            'cpu_usage': metric_data['cpu_usage'],
                            'rx_data': metric_data['rx_data'],
                            'tx_data': metric_data['tx_data'],
                            'pids': pids
                        }
                        resultados.append(registro)
                        
                    except Exception as e:
                        print(f"Erro processando linha da tabela {tabela}: {str(e)}")
                        continue
                        
            except Exception as e:
                print(f"Erro acessando tabela {tabela}: {str(e)}")
                continue
                
        conn.close()
        return resultados
        
    except Exception as e:
        print(f"Erro geral ao acessar banco: {str(e)}")
        return []

@app.route('/upload', methods=['POST'])
def upload_sqlite():
    global db_path
    
    if 'file' not in request.files:
        return jsonify({"erro": "Nenhum arquivo enviado"}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"erro": "Nenhum arquivo selecionado"}), 400
        
    if not file.filename.lower().endswith(".sqlite"):
        return jsonify({"erro": "Arquivo inválido. Envie um arquivo .sqlite"}), 400
    
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        try:
            conn = sqlite3.connect(file_path)
            conn.close()
        except:
            os.remove(file_path)
            return jsonify({"erro": "Arquivo SQLite inválido"}), 400
            
        db_path = file_path
        return jsonify({"mensagem": "Arquivo recebido com sucesso", "caminho": file_path}), 200
        
    except Exception as e:
        return jsonify({"erro": f"Falha ao salvar arquivo: {str(e)}"}), 500

@app.route('/processos', methods=['GET'])
def get_processos():
    try:
        start = request.args.get('start', type=int)
        end = request.args.get('end', type=int)
        
        dados = carregar_dados()
        if not dados:
            return jsonify({"erro": "Nenhum dado disponível"}), 404
        
        if start is not None:
            dados = [p for p in dados if isinstance(p.get("timestamp"), (int, float)) and p["timestamp"] >= start]
        if end is not None:
            dados = [p for p in dados if isinstance(p.get("timestamp"), (int, float)) and p["timestamp"] <= end]
            
        return jsonify(dados), 200
        
    except Exception as e:
        return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)