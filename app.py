import os
import json
from flask import Flask, request, jsonify, render_template
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Carregar variáveis de ambiente do .env
load_dotenv()

from utils.gemini_service import extract_document_info
from utils.dataset import find_match_in_text, find_atribuido_match
from utils.sheets_service import append_to_sheet

app = Flask(__name__)

# Diretório para salvar uploads temporários
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process-document', methods=['POST'])
def process_document():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nenhum arquivo selecionado"}), 400
        
    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Apenas arquivos PDF são permitidos"}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)

    try:
        # 1. Extrair texto do PDF
        text = ""
        with fitz.open(filepath) as doc:
            for page in doc:
                text += page.get_text()
                
        if not text.strip():
            return jsonify({"error": "O documento PDF não contém texto extraível."}), 400

        # 2. Chamar Gemini API para extrair os 3 campos
        gemini_result_str = extract_document_info(text)
        try:
            gemini_data = json.loads(gemini_result_str)
            # Normalizar chaves (evitar problemas de maiúsculas/minúsculas)
            normalized_data = {}
            for k, v in gemini_data.items():
                k_clean = k.strip()
                normalized_data[k_clean] = v
                if k_clean.lower() == 'processo_judicial':
                    normalized_data['Processo_Judicial'] = v
                elif k_clean.lower() in ['data_judicial', 'data_judicial:']:
                    normalized_data['Data_Judicial'] = v
                elif k_clean.lower() == 'num_sei':
                    normalized_data['Num_SEI'] = v
                elif k_clean.lower() in ['atribuido', 'atribuído']:
                    normalized_data['Atribuido'] = v
                elif k_clean.lower() in ['autuacao_cdj', 'autuação_cdj']:
                    normalized_data['Autuacao_CDJ'] = v
            gemini_data = normalized_data
        except json.JSONDecodeError:
            gemini_data = {
                "Processo_Judicial": "Não identificado",
                "Data_Judicial": "Não identificado", 
                "Num_SEI": "Não identificado",
                "Atribuido": "Não identificado",
                "Autuacao_CDJ": "Não identificado"
            }

        # Extração direta do número do processo judicial via Python
        processo = ""
        import re

        # 1. Procurar por padrão CNJ (xxxxxxx-xx.xxxx.x.xx.xxxx) com tolerância a espaços
        cnj_pattern = r'\b\d{7}\s*-\s*\d{2}\s*\.\s*\d{4}\s*\.\s*\d\s*\.\s*\d{2}\s*\.\s*\d{4}\b'
        match_cnj = re.search(cnj_pattern, text)
        if match_cnj:
            raw_cnj = match_cnj.group(0)
            clean_cnj = re.sub(r'\s+', '', raw_cnj)
            if clean_cnj:
                processo = clean_cnj

        # 2. Se não encontrou padrão CNJ, buscar após a etiqueta "Processo Judicial:"
        if not processo:
            idx = text.lower().find("processo judicial:")
            if idx != -1:
                after_text = text[idx + len("processo judicial:"):].strip()
                match_num = re.search(r'^([\d\.\-\/\s]+)', after_text)
                if match_num:
                    raw_num = match_num.group(1).strip()
                    clean_num = raw_num.replace(" ", "").replace("\n", "").replace("\r", "")
                    if clean_num:
                        processo = clean_num

        # 3. Fallback para o valor extraído pelo Gemini
        if not processo or processo == "Não identificado" or processo == "Erro":
            processo = gemini_data.get('Processo_Judicial', 'Não identificado')

        # Extração direta pós "Última Distribuição:" via Python (Regex)
        data_judicial = gemini_data.get('Data_Judicial', '')
        idx_dist = text.lower().find("última distribuição:")
        if idx_dist == -1:
            idx_dist = text.lower().find("ultima distribuicao:")
        if idx_dist != -1:
            after_dist = text[idx_dist + len("última distribuição:"):].strip()
            # Procurar pela primeira ocorrência de uma data no formato DD/MM/AAAA
            match_date = re.search(r'(\d{2}/\d{2}/\d{4})', after_dist)
            if match_date:
                data_judicial = match_date.group(1).strip()

        if not data_judicial or data_judicial == "Não identificado" or data_judicial == "Erro":
            data_judicial = gemini_data.get('Data_Judicial', 'Não identificado')

        # Extração direta pós "assinado eletronicamente por" ou "assinado digitalmente por"
        atribuido = gemini_data.get('Atribuido', '')
        for marker in ["assinado eletronicamente por", "assinado digitalmente por"]:
            idx_sig = text.lower().find(marker)
            if idx_sig != -1:
                after_sig = text[idx_sig + len(marker):].strip()
                if after_sig.startswith(':'):
                    after_sig = after_sig[1:].strip()
                # A regex procura por uma sequência de palavras correspondentes ao nome próprio
                match_name = re.search(r'^([A-Za-záàâãéèêíïóôõöúçñÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s]+)', after_sig)
                if match_name:
                    raw_name = match_name.group(1).strip()
                    raw_name = re.sub(r'\s+', ' ', raw_name)
                    for stop_word in [" em ", " cpf", " matricula", " matrícula", " cargo", " de autoria"]:
                        stop_idx = raw_name.lower().find(stop_word)
                        if stop_idx != -1:
                            raw_name = raw_name[:stop_idx].strip()
                    if raw_name:
                        atribuido = raw_name
                        break

        if not atribuido or atribuido == "Erro":
            atribuido = gemini_data.get('Atribuido', 'Não identificado')

        # Buscar correspondência e padronizar o nome do funcionário
        atribuido = find_atribuido_match(atribuido)

        # Extração direta da Autuação na CDJ via Python (Regex)
        autuacao_cdj = gemini_data.get('Autuacao_CDJ', '')
        for marker in ["assinado eletronicamente por", "assinado digitalmente por"]:
            idx_sig = text.lower().find(marker)
            if idx_sig != -1:
                after_sig = text[idx_sig + len(marker):]
                # Buscar a primeira data no formato DD/MM/AAAA após a assinatura
                match_date = re.search(r'(\d{2}/\d{2}/\d{4})', after_sig)
                if match_date:
                    autuacao_cdj = match_date.group(1).strip()
                    break

        if not autuacao_cdj or autuacao_cdj == "Não identificado" or autuacao_cdj == "Erro":
            autuacao_cdj = gemini_data.get('Autuacao_CDJ', 'Não identificado')
            
        # 3. Chamar Dataset para encontrar Objeto e Setor
        dataset_match = find_match_in_text(text)
        
        observacoes = dataset_match.get('chave_encontrada', '')

        # 4. Inserir no Google Sheets
        reu = dataset_match.get('reu', '')
        num_sei = gemini_data.get('Num_SEI', '')
        objeto = dataset_match.get('objeto', '')
        setor = dataset_match.get('setor', '')
        
        sheet_result = append_to_sheet(data_judicial, processo, reu, num_sei, objeto, setor, atribuido, observacoes, autuacao_cdj)
        
        if sheet_result.get('status') == 'error':
            return jsonify({
                "error": "Falha ao salvar no Google Sheets",
                "details": sheet_result.get('message')
            }), 500

        return jsonify({
            "success": True,
            "extracted": {
                "Processo_Judicial": processo,
                "Réu": reu,
                "Data_Judicial": data_judicial,
                "Num_SEI": num_sei,
                "Objeto": objeto,
                "Setor": setor,
                "Destinatário": setor,
                "Atribuido": atribuido,
                "Observacoes": observacoes,
                "Autuacao_CDJ": autuacao_cdj
            }
        })
    except Exception as e:
        print(f"Erro ao processar: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500
    finally:
        # Opcional: remover o arquivo após o processamento
        if os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
