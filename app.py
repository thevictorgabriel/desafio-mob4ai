from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import tempfile
import pandas as pd

app = Flask(__name__)
CORS(app)

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
        dfs = []
        
        for tabela in tabelas:
            try:
                cursor.execute(f"PRAGMA table_info({tabela});")
                colunas = [col[1] for col in cursor.fetchall()]
                print(f"Colunas em {tabela}:", colunas)
                
                query = "SELECT "
                selects = []
                
                if 'PackageName' in colunas:
                    selects.append("PackageName as package_name")
                if 'Pids' in colunas:
                    selects.append("Pids as pids")
                if 'Metrics' in colunas:
                    selects.append("Metrics as metrics")
                if 'ByteSize' in colunas:
                    selects.append("ByteSize as byte_size")
                
                if not selects:
                    continue
                    
                query += ", ".join(selects) + f" FROM {tabela}"
                df = pd.read_sql_query(query, conn)
                
                if 'pids' in df.columns:
                    df['pids'] = df['pids'].astype(str)
                if 'metrics' in df.columns:
                    df['metrics'] = df['metrics'].astype(str)
                
                dfs.append(df)
                
            except Exception as e:
                print(f"Erro processando {tabela}: {str(e)}")
                continue
                
        conn.close()
        
        if dfs:
            df_unificado = pd.concat(dfs, ignore_index=True)
            return df_unificado.to_dict(orient="records")
            
    except Exception as e:
        print(f"Erro ao acessar banco: {str(e)}")
        
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