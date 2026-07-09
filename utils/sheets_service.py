import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

# Defina as permissões necessárias
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# O ID da planilha. Pode ser extraído da URL: https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', 'COLOQUE_SEU_ID_AQUI')
RANGE_NAME = 'Geral!A:I' # Preenchendo da coluna A a I na aba "Geral".

def get_sheets_service():
    creds = None
    cred_path = os.path.join(os.path.dirname(__file__), '..', 'credenciais.json')
    
    if os.path.exists(cred_path):
        creds = service_account.Credentials.from_service_account_file(
                cred_path, scopes=SCOPES)
    else:
        raise Exception("Arquivo credenciais.json não encontrado. Coloque-o na raiz do projeto.")

    service = build('sheets', 'v4', credentials=creds)
    return service

def append_to_sheet(data_judicial, processo_judicial, reu, num_sei, objeto, setor, atribuido, observacoes, autuacao_cdj):
    """
    Appends a row to the Google Sheet directly after the last populated row.
    """
    try:
        service = get_sheets_service()
        
        # 1. Ler todos os valores existentes para encontrar a última linha realmente preenchida
        sheet_data = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Geral!A:I'
        ).execute()
        
        existing_values = sheet_data.get('values', [])
        
        # Encontrar a última linha preenchida analisando de trás para frente
        last_filled_idx = len(existing_values)
        while last_filled_idx > 0:
            row_vals = existing_values[last_filled_idx - 1]
            # Se a linha contiver qualquer valor preenchido (não apenas células vazias)
            if any(str(cell).strip() for cell in row_vals):
                break
            last_filled_idx -= 1
            
        next_row = last_filled_idx + 1
        write_range = f'Geral!A{next_row}:I{next_row}'
        
        # The order of values MUST match your sheet columns!
        # Assuming the columns are: Data_Judicial | Processo_Judicial | Réu | Num_SEI | Objeto | Destinatário | Atribuído | Observações | Autuação na CDJ
        values = [
            [data_judicial, processo_judicial, reu, num_sei, objeto, setor, atribuido, observacoes, autuacao_cdj]
        ]
        body = {
            'values': values
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=write_range,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return {"status": "success", "updates": result}
    except Exception as e:
        print(f"Erro ao inserir no Google Sheets: {e}")
        return {"status": "error", "message": str(e)}
