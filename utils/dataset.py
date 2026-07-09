import pandas as pd
import os
import unicodedata

DATASET_PATH = os.path.join(os.path.dirname(__file__), '..', 'dataset_aut_sesap.xlsx')
DATASET_REU_PATH = os.path.join(os.path.dirname(__file__), '..', 'dataset_aut_sesap_reu.xlsx')
DATASET_ATRIBUIDOS_PATH = os.path.join(os.path.dirname(__file__), '..', 'dataset_aut_sesap_atribuidos.xlsx')

def remove_accents(t: str) -> str:
    """
    Converts string to lowercase and removes diacritics/accents.
    Also handles unicode replacement characters like \ufffd.
    """
    if not isinstance(t, str):
        t = str(t)
    t = t.lower()
    t = t.replace('\ufffd', '')
    t = unicodedata.normalize('NFKD', t)
    return "".join(c for c in t if not unicodedata.combining(c))

def is_match(keyword_norm: str, text_normalized: str) -> bool:
    """
    Checks if a normalized keyword matches the normalized text.
    If the keyword is short (less than 4 characters), it must match as a whole word.
    Otherwise, a substring match is allowed.
    """
    if not keyword_norm:
        return False
    if len(keyword_norm) >= 4:
        return keyword_norm in text_normalized
    # Match as whole word for short keywords
    cleaned_text = "".join(c if c.isalnum() else " " for c in text_normalized)
    return keyword_norm in cleaned_text.split()

def find_match_in_text(text: str):
    """
    Reads the local datasets and searches for 'chave' in the extracted text.
    Returns a dict with 'objeto', 'setor', 'reu' and 'chave_encontrada'.
    """
    result = {"objeto": "Não encontrado", "setor": "Não encontrado", "reu": "Não encontrado", "chave_encontrada": ""}
    text_normalized = remove_accents(text)

    # Busca Objeto e Setor
    try:
        df = pd.read_excel(DATASET_PATH)
        df.columns = df.columns.str.strip().str.lower()
        
        if 'chave' in df.columns and 'objeto' in df.columns and 'setor' in df.columns:
            for index, row in df.iterrows():
                chave_str = str(row['chave']).strip()
                if pd.isna(row['chave']) or not chave_str:
                    continue
                
                # ATENÇÃO: Dividir APENAS por ponto e vírgula ";", pois a vírgula "," faz parte dos termos
                chaves_originais = [c.strip() for c in chave_str.split(';')]
                match_found = False
                matched_key = ""
                for c_orig in chaves_originais:
                    if not c_orig:
                        continue
                    
                    # Se a chave contiver "+", tratamos como operador AND (todas as partes devem estar presentes)
                    if '+' in c_orig:
                        parts_orig = [p.strip() for p in c_orig.split('+')]
                        parts_norm = [remove_accents(p) for p in parts_orig if p]
                        if parts_norm and all(is_match(p, text_normalized) for p in parts_norm):
                            match_found = True
                            matched_key = c_orig
                            break
                    else:
                        c_norm = remove_accents(c_orig)
                        if is_match(c_norm, text_normalized):
                            match_found = True
                            matched_key = c_orig
                            break
                
                if match_found:
                    result["objeto"] = str(row['objeto']).strip()
                    result["setor"] = str(row['setor']).strip()
                    result["chave_encontrada"] = matched_key
                    break # Para no primeiro match
        else:
            print("Colunas 'chave', 'objeto', 'setor' não encontradas no dataset principal.")
    except Exception as e:
        print(f"Erro ao ler dataset principal: {e}")
        result["objeto"] = "Erro de leitura"
        result["setor"] = "Erro de leitura"

    # Busca Réu
    try:
        if os.path.exists(DATASET_REU_PATH):
            df_reu = pd.read_excel(DATASET_REU_PATH)
            df_reu.columns = df_reu.columns.str.strip().str.lower()
            
            if 'chave' in df_reu.columns and 'reu' in df_reu.columns:
                for index, row in df_reu.iterrows():
                    chave_str = str(row['chave']).strip()
                    if pd.isna(row['chave']) or not chave_str:
                        continue
                    
                    chaves_originais = [c.strip() for c in chave_str.split(';')]
                    match_found = False
                    for c_orig in chaves_originais:
                        if not c_orig:
                            continue
                        
                        # Se a chave do réu contiver "+", todas as partes devem estar no texto
                        if '+' in c_orig:
                            parts_orig = [p.strip() for p in c_orig.split('+')]
                            parts_norm = [remove_accents(p) for p in parts_orig if p]
                            if parts_norm and all(is_match(p, text_normalized) for p in parts_norm):
                                match_found = True
                                break
                        else:
                            c_norm = remove_accents(c_orig)
                            if is_match(c_norm, text_normalized):
                                match_found = True
                                break
                    
                    if match_found:
                        reu_val = str(row['reu']).strip()
                        if reu_val.lower() != 'nan' and reu_val:
                            result["reu"] = reu_val
                        break # Para no primeiro match
            else:
                print("Colunas 'chave' e 'reu' não encontradas no dataset de réus.")
    except Exception as e:
        print(f"Erro ao ler dataset de réus: {e}")
        result["reu"] = "Erro de leitura"

    return result

def find_atribuido_match(extracted_name: str) -> str:
    """
    Looks up the extracted signer name in dataset_aut_sesap_atribuidos.xlsx.
    If a match is found based on 'chave', returns the corresponding 'atribuido' value.
    Otherwise, returns the original extracted name.
    """
    if not extracted_name or extracted_name in ["Não identificado", "Erro"]:
        return extracted_name
        
    try:
        if os.path.exists(DATASET_ATRIBUIDOS_PATH):
            df = pd.read_excel(DATASET_ATRIBUIDOS_PATH)
            df.columns = df.columns.str.strip().str.lower()
            
            if 'chave' in df.columns and 'atribuido' in df.columns:
                extracted_norm = remove_accents(extracted_name).strip()
                
                # First pass: exact match
                for index, row in df.iterrows():
                    chave_val = str(row['chave']).strip()
                    if pd.isna(row['chave']) or not chave_val:
                        continue
                    chaves = [remove_accents(c.strip()) for c in chave_val.split(';')]
                    if any(c == extracted_norm for c in chaves if c):
                        atrib_val = str(row['atribuido']).strip()
                        if atrib_val.lower() != 'nan' and atrib_val:
                            return atrib_val

                # Second pass: containment match
                for index, row in df.iterrows():
                    chave_val = str(row['chave']).strip()
                    if pd.isna(row['chave']) or not chave_val:
                        continue
                    chaves = [remove_accents(c.strip()) for c in chave_val.split(';')]
                    if any((c in extracted_norm or extracted_norm in c) for c in chaves if c):
                        atrib_val = str(row['atribuido']).strip()
                        if atrib_val.lower() != 'nan' and atrib_val:
                            return atrib_val
            else:
                print("Colunas 'chave' e 'atribuido' não encontradas no dataset de atribuição.")
    except Exception as e:
        print(f"Erro ao ler dataset de atribuição: {e}")
        
    return extracted_name
