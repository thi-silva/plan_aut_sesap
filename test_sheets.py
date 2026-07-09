import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID')
RANGE_NAME = 'aba_teste!A:E'

def test_connection():
    if not SPREADSHEET_ID or SPREADSHEET_ID == 'SEU_ID_AQUI':
        print("Erro: SPREADSHEET_ID não configurado no .env")
        return
        
    cred_path = 'credenciais.json'
    if not os.path.exists(cred_path):
        print("Erro: credenciais.json não encontrado na raiz.")
        return

    try:
        creds = service_account.Credentials.from_service_account_file(
            cred_path, scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=creds)
        
        # Tenta ler a planilha para testar a permissão (só ler as propriedades, não gasta quota pesada)
        sheet_metadata = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        print(f"Sucesso! Planilha encontrada: {sheet_metadata.get('properties', {}).get('title', 'Sem Título')}")
        
        # Testar se a aba 'aba_teste' existe
        sheets = sheet_metadata.get('sheets', [])
        abas = [s['properties']['title'] for s in sheets]
        print(f"Abas encontradas na planilha: {abas}")
        
        if 'aba_teste' not in abas:
            print(f"ERRO: A aba 'aba_teste' não foi encontrada. As abas disponíveis são: {abas}")
            return
            
        print("Tudo certo para gravar na planilha!")
        
    except Exception as e:
        print(f"Erro ao conectar com Google Sheets API:\n{str(e)}")

if __name__ == "__main__":
    test_connection()
