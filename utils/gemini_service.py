import os
from google import genai
from google.genai import types

def extract_document_info(text: str):
    """
    Extracts 'Processo_judicial', 'Classe', and 'Num_SEI' from the document text
    using Google Gemini API.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise Exception("A variável de ambiente GEMINI_API_KEY não está configurada.")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
Você é um assistente especializado em extração de dados jurídicos e administrativos.
Analise o seguinte texto de um documento e extraia as seguintes informações:
1. "Processo_Judicial": O número do processo judicial. ATENÇÃO: Identifique o trecho "Processo Judicial:" no documento e extraia/recorte rigorosamente apenas o recorte da numeração que aparece logo após esse trecho (por exemplo, "0801234-56.2023.8.20.5001" ou similar). Não inclua o texto "Processo Judicial:", apenas o número/código subsequente.
2. "Data_Judicial": A data da última distribuição do processo. ATENÇÃO: Identifique o trecho "Última Distribuição:" no documento e extraia apenas a data no formato DD/MM/AAAA que aparece logo após esse trecho.
3. "Num_SEI": O número do SEI (geralmente encontrado após "Processo nº" ou similar).
4. "Atribuido": O nome da pessoa associada à assinatura eletrônica. ATENÇÃO: Identifique o trecho "assinado eletronicamente por" (ou variações como "assinado digitalmente por") e extraia/recorte apenas o nome próprio da pessoa que aparece logo após esse trecho. Não inclua datas, CPFs, horários ou cargos (por exemplo, se constar "assinado eletronicamente por JOÃO DA SILVA em 12/03/2026", extraia apenas "JOÃO DA SILVA").
5. "Autuacao_CDJ": A data da autuação ou assinatura do servidor. ATENÇÃO: Identifique a data no formato DD/MM/AAAA que aparece logo após o nome e o cargo do servidor no trecho de assinatura (por exemplo, no trecho "...assinado eletronicamente por JOÃO DA SILVA - Técnico Judiciário em 12/03/2026", extraia apenas "12/03/2026").

Responda ESTRITAMENTE em formato JSON, sem marcações markdown ou blocos de código extra. Apenas o JSON válido.
Exemplo de saída esperada:
{{
  "Processo_Judicial": "0000000-00.0000.0.00.0000",
  "Data_Judicial": "20/05/2026",
  "Num_SEI": "00000.000000/0000-00",
  "Atribuido": "JOÃO DA SILVA",
  "Autuacao_CDJ": "12/03/2026"
}}

Se uma informação não estiver presente no texto, retorne null ou string vazia para aquele campo.

TEXTO DO DOCUMENTO:
{text}
"""

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        
        # O resultado deve ser uma string JSON
        return response.text
    except Exception as e:
        print(f"Erro na extração com Gemini: {e}")
        return '{"Processo_Judicial": "Erro", "Data_Judicial": "Erro", "Num_SEI": "Erro", "Atribuido": "Erro", "Autuacao_CDJ": "Erro"}'
