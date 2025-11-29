from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
import tempfile
import zipfile
from typing import List
import uuid
import requests
from fastapi import Request
from fastapi.responses import StreamingResponse
import convertapi

app = FastAPI(title="PDF Platform", description="Plataforma de manipulação de PDFs")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"
Path(UPLOAD_DIR).mkdir(exist_ok=True)
Path(OUTPUT_DIR).mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuração da ConvertAPI
# IMPORTANTE: Configure a variável de ambiente CONVERTAPI_SECRET no Railway
def get_convertapi_secret():
    """Obtém a chave da ConvertAPI, tentando ler novamente a variável de ambiente"""
    # Importar convertapi dentro da função para evitar problemas de escopo
    import convertapi
    
    secret = os.environ.get("CONVERTAPI_SECRET")
    if secret:
        # A biblioteca ConvertAPI usa api_secret como propriedade que define api_credentials internamente
        convertapi.api_secret = secret
        
        # Verificar se api_credentials foi configurado automaticamente
        # Se não, tentar configurar manualmente
        try:
            import convertapi.client
            # A biblioteca pode usar convertapi.client.api_credentials
            if not hasattr(convertapi.client, 'api_credentials') or convertapi.client.api_credentials is None:
                # Tentar configurar diretamente no módulo client
                convertapi.client.api_credentials = secret
        except Exception as e:
            print(f"Erro ao configurar api_credentials no client: {e}")
        
        # Também tentar configurar no módulo principal se existir
        try:
            if hasattr(convertapi, 'api_credentials'):
                convertapi.api_credentials = secret
        except:
            pass
    return secret

CONVERTAPI_SECRET = get_convertapi_secret()
if not CONVERTAPI_SECRET:
    print("AVISO: CONVERTAPI_SECRET não configurada. Configure a variável de ambiente no Railway.")
else:
    # Garantir que está configurado corretamente
    print(f"ConvertAPI configurada: {CONVERTAPI_SECRET[:10]}...")
    # Verificar se api_credentials está configurado
    try:
        import convertapi.client
        if hasattr(convertapi.client, 'api_credentials'):
            print(f"api_credentials no client: {convertapi.client.api_credentials is not None}")
    except:
        pass

# Configuração do Telegram
# IMPORTANTE: Configure as variáveis de ambiente TELEGRAM_TOKEN e TELEGRAM_CHAT_ID no Railway
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def notify_telegram(message: str):
    # Só envia notificação se as variáveis estiverem configuradas
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=data, timeout=3)
    except Exception:
        pass

def get_country_from_ip(ip):
    try:
        r = requests.get(f"https://ipapi.co/{ip}/country_name/", timeout=2)
        if r.status_code == 200:
            return r.text.strip()
    except Exception:
        pass
    return "Desconhecido"

@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    return """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PDF Platform - Lobios</title>
        <link rel="icon" type="image/png" href="/static/logo.png"/>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Quicksand:wght@500;700&display=swap" rel="stylesheet">
        <style>
            * { box-sizing: border-box; }
            :root {
                --lobios-purple: #7b3294;
                --lobios-purple-light: #a259c6;
                --lobios-purple-hover: #6a2a82;
                --lobios-bg: #f8f9fa;
                --lobios-card: #ffffff;
                --lobios-gray: #e9ecef;
                --lobios-dark: #212529;
                --lobios-text: #495057;
                --lobios-border: #dee2e6;
            }
            body {
                margin: 0; padding: 0; 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--lobios-bg);
                color: var(--lobios-dark);
                line-height: 1.6;
            }
            .hero-section {
                background: linear-gradient(135deg, var(--lobios-purple) 0%, var(--lobios-purple-light) 100%);
                color: white;
                padding: 80px 20px 60px;
                text-align: center;
                margin-bottom: 60px;
            }
            .hero-section h1 {
                font-size: 3.5rem;
                font-weight: 700;
                margin: 0 0 20px;
                letter-spacing: -0.02em;
            }
            .hero-section p {
                font-size: 1.25rem;
                margin: 0 auto;
                opacity: 0.95;
                max-width: 700px;
            }
            .sidebar {
                position: fixed; left: 0; top: 0; bottom: 0; width: 260px; 
                background: var(--lobios-card); 
                box-shadow: 2px 0 12px rgba(0,0,0,0.05);
                z-index: 100;
                overflow-y: auto;
            }
            .sidebar-header {
                padding: 30px 20px;
                border-bottom: 1px solid var(--lobios-border);
            }
            .sidebar img {
                width: 160px; display: block; margin: 0 auto;
            }
            .sidebar nav {
                padding: 20px 0;
            }
            .sidebar nav a {
                display: block; 
                color: var(--lobios-text); 
                text-decoration: none; 
                padding: 14px 24px; 
                font-size: 15px;
                font-weight: 500;
                transition: all 0.2s ease;
                border-left: 3px solid transparent;
            }
            .sidebar nav a:hover {
                background: rgba(123, 50, 148, 0.05);
                color: var(--lobios-purple);
            }
            .sidebar nav a.active {
                background: rgba(123, 50, 148, 0.1);
                color: var(--lobios-purple);
                border-left-color: var(--lobios-purple);
                font-weight: 600;
            }
            .main {
                margin-left: 260px; 
                min-height: 100vh;
            }
            .container {
                max-width: 1400px; 
                margin: 0 auto; 
                padding: 40px 30px;
            }
            .section-header {
                margin-bottom: 40px;
            }
            .section-header h2 {
                color: var(--lobios-purple);
                margin: 0 0 12px; 
                font-size: 2.5rem;
                font-weight: 700;
                letter-spacing: -0.02em;
            }
            .section-header p {
                color: var(--lobios-text);
                font-size: 1.1rem;
                margin: 0;
            }
            .tools-grid {
                display: grid; 
                grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); 
                gap: 28px;
            }
            .tool-card {
                background: var(--lobios-card); 
                border-radius: 16px; 
                padding: 32px 28px; 
                box-shadow: 0 2px 8px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06);
                display: flex; 
                flex-direction: column; 
                transition: all 0.3s ease;
                border: 1px solid var(--lobios-border);
            }
            .tool-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 4px 16px rgba(123,50,148,0.12), 0 12px 32px rgba(0,0,0,0.08);
            }
            .tool-card h3 {
                color: var(--lobios-purple); 
                margin: 0 0 20px; 
                font-size: 1.4rem; 
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .tool-card.disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            .tool-card.disabled:hover {
                transform: none;
            }
            .file-input { 
                width: 100%; 
                padding: 16px; 
                border: 2px dashed var(--lobios-purple-light); 
                border-radius: 12px; 
                margin-bottom: 16px; 
                cursor: pointer; 
                background: rgba(123, 50, 148, 0.03);
                font-size: 14px;
                transition: all 0.2s;
            }
            .file-input:hover { 
                border-color: var(--lobios-purple); 
                background: rgba(123, 50, 148, 0.06);
            }
            .btn { 
                background: var(--lobios-purple); 
                color: white; 
                border: none; 
                padding: 16px 24px; 
                border-radius: 12px; 
                cursor: pointer; 
                width: 100%; 
                font-size: 16px; 
                font-weight: 600; 
                transition: all 0.2s;
                box-shadow: 0 2px 8px rgba(123,50,148,0.2);
            }
            .btn:hover { 
                background: var(--lobios-purple-hover); 
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(123,50,148,0.3);
            }
            .btn:active {
                transform: translateY(0);
            }
            .btn:disabled { 
                background: #adb5bd; 
                cursor: not-allowed;
                box-shadow: none;
            }
            .btn:disabled:hover {
                transform: none;
            }
            input[type="text"], input[type="number"], input[type="password"] {
                width: 100%; 
                padding: 14px 16px; 
                margin: 8px 0 16px; 
                border: 1.5px solid var(--lobios-border); 
                border-radius: 10px; 
                font-size: 15px;
                transition: all 0.2s;
                font-family: inherit;
            }
            input[type="text"]:focus, input[type="number"]:focus, input[type="password"]:focus {
                outline: none;
                border-color: var(--lobios-purple);
                box-shadow: 0 0 0 3px rgba(123,50,148,0.1);
            }
            .result { 
                margin-top: 20px; 
                padding: 16px; 
                background: rgba(123, 50, 148, 0.08); 
                border-radius: 10px; 
                display: none; 
                color: var(--lobios-dark);
                border: 1px solid rgba(123, 50, 148, 0.15);
            }
            .result a {
                color: var(--lobios-purple);
                font-weight: 600;
                text-decoration: none;
            }
            .result a:hover {
                text-decoration: underline;
            }
            .error { 
                background: #fee; 
                color: #c33; 
                border-color: #fcc;
            }
            .loading { 
                display: none; 
                text-align: center; 
                margin-top: 16px;
                color: var(--lobios-purple);
                font-weight: 500;
            }
            .privacy-btn {
                position: fixed;
                right: 30px;
                bottom: 30px;
                z-index: 99;
                background: var(--lobios-card);
                color: var(--lobios-purple);
                border: 2px solid var(--lobios-purple);
                padding: 12px 24px;
                border-radius: 30px;
                font-weight: 600;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
                cursor: pointer;
                transition: all 0.2s;
                font-size: 14px;
            }
            .privacy-btn:hover {
                background: var(--lobios-purple);
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(123,50,148,0.3);
            }
            .modal-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                background: rgba(0,0,0,0.5);
                z-index: 1000;
                align-items: center;
                justify-content: center;
                backdrop-filter: blur(4px);
            }
            .modal-content {
                background: var(--lobios-card);
                border-radius: 20px;
                max-width: 900px;
                width: 95vw;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                position: relative;
                max-height: 90vh;
                overflow-y: auto;
            }
            .modal-close {
                position: absolute;
                top: 20px;
                right: 24px;
                font-size: 32px;
                cursor: pointer;
                color: var(--lobios-text);
                line-height: 1;
                transition: color 0.2s;
            }
            .modal-close:hover {
                color: var(--lobios-purple);
            }
            @media (max-width: 1024px) {
                .sidebar { width: 200px; }
                .main { margin-left: 200px; }
                .hero-section h1 { font-size: 2.5rem; }
                .tools-grid { grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; }
            }
            @media (max-width: 768px) {
                .sidebar { 
                    transform: translateX(-100%);
                    transition: transform 0.3s;
                }
                .sidebar.open {
                    transform: translateX(0);
                }
                .main { margin-left: 0; }
                .hero-section { padding: 60px 20px 40px; }
                .hero-section h1 { font-size: 2rem; }
                .hero-section p { font-size: 1rem; }
                .container { padding: 20px 15px; }
                .tools-grid { grid-template-columns: 1fr; gap: 20px; }
                .section-header h2 { font-size: 2rem; }
            }
            @media (max-width: 900px) {
                .sidebar { width: 60px; padding-top: 18px; }
                .sidebar img { width: 38px; margin-bottom: 18px; }
                .sidebar nav a { font-size: 0; padding: 12px 10px; }
                .main { margin-left: 60px; }
            }
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="sidebar-header">
            <img src="/static/logo.png" alt="Lobios">
            </div>
            <nav id="sidebar-categories">
                <a href="#" class="category-link active" data-category="organizar">Organizar PDF</a>
                <a href="#" class="category-link" data-category="otimizar">Otimizar PDF</a>
                <a href="#" class="category-link" data-category="converter-em">Converter em PDF</a>
                <a href="#" class="category-link" data-category="converter-de">Converter de PDF</a>
                <a href="#" class="category-link" data-category="editar">Editar PDF</a>
                <a href="#" class="category-link" data-category="seguranca">Segurança do PDF</a>
            </nav>
        </div>
        <div class="main">
            <div class="hero-section">
                <h1>Todas as ferramentas PDF que você precisa em um só lugar</h1>
                <p>Ferramentas online 100% gratuitas e fáceis de usar! Junte, divida, comprima, converta, rotacione, desbloqueie e adicione marca d'água em PDFs com apenas alguns cliques.</p>
            </div>
            <div class="container">
                <div class="section-header">
                    <h2 id="category-title">Organizar PDF</h2>
                    <p id="category-desc">Manipule e organize seus arquivos PDF facilmente</p>
                </div>
                <div id="category-functions">
                    <!-- ORGANIZAR PDF -->
                    <div class="tools-grid" id="organizar" style="display: grid;">
                        <!-- Juntar PDF (funcional) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">🧩 Juntar PDF</h3>
                            <input type="file" id="mergePdfs" accept=".pdf" multiple class="file-input input-full">
                            <button onclick="mergePdfs()" class="btn input-full">Juntar Arquivos</button>
                            <div class="loading" id="loadingMerge">Juntando...</div>
                            <div class="result" id="resultMerge"></div>
                        </div>
                        <!-- Dividir PDF (funcional) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">✂️ Dividir PDF</h3>
                            <input type="file" id="splitPdf" accept=".pdf" class="file-input input-full">
                            <input type="number" placeholder="Página inicial" id="startPage" min="1" class="input-full">
                            <input type="number" placeholder="Página final" id="endPage" min="1" class="input-full">
                            <button onclick="splitPdf()" class="btn input-full">Extrair Páginas</button>
                            <div class="loading" id="loadingSplit">Extraindo...</div>
                            <div class="result" id="resultSplit"></div>
                        </div>
                        <!-- Remover páginas (nova função) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">❌ Remover páginas</h3>
                            <input type="file" id="removePagesPdf" accept=".pdf" class="file-input input-full">
                            <input type="text" placeholder="Ex: 2,4,7-9" id="removePagesList" class="input-full">
                            <button onclick="removePages()" class="btn input-full">Remover Páginas</button>
                            <div class="loading" id="loadingRemovePages">Removendo...</div>
                            <div class="result" id="resultRemovePages"></div>
                        </div>
                        <!-- Extrair páginas (nova função) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">📤 Extrair páginas</h3>
                            <input type="file" id="extractPagesPdf" accept=".pdf" class="file-input input-full">
                            <input type="text" placeholder="Ex: 1,3,5-7" id="extractPagesList" class="input-full">
                            <button onclick="extractPages()" class="btn input-full">Extrair Páginas</button>
                            <div class="loading" id="loadingExtractPages">Extraindo...</div>
                            <div class="result" id="resultExtractPages"></div>
                        </div>
                        <!-- Organizar PDF (nova função) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">🔀 Organizar PDF</h3>
                            <input type="file" id="organizePdf" accept=".pdf" class="file-input input-full">
                            <input type="text" placeholder="Nova ordem (Ex: 3,1,2,5,4)" id="organizeOrder" class="input-full">
                            <button onclick="organizePdfPages()" class="btn input-full">Organizar Páginas</button>
                            <div class="loading" id="loadingOrganizePdf">Organizando...</div>
                            <div class="result" id="resultOrganizePdf"></div>
                        </div>
                        <!-- Digitalizar PDF (em breve) -->
                        <div class="tool-card disabled"><h3>📷 Digitalizar PDF</h3><p>Em breve</p></div>
                    </div>
                    <!-- OTIMIZAR PDF -->
                    <div class="tools-grid" id="otimizar" style="display: none;">
                        <!-- Comprimir PDF (funcional) -->
                        <div class="tool-card">
                            <h3>🗜️ Comprimir PDF</h3>
                            <input type="file" id="compressPdf" accept=".pdf" class="file-input">
                            <button onclick="compressPdf()" class="btn">Comprimir Arquivo</button>
                            <div class="loading" id="loadingCompress">Comprimindo...</div>
                            <div class="result" id="resultCompress"></div>
                        </div>
                        <!-- Em breve -->
                        <div class="tool-card disabled"><h3>🛠️ Reparar PDF</h3><p>Em breve</p></div>
                        <div class="tool-card disabled"><h3>📝 OCR PDF</h3><p>Em breve</p></div>
                    </div>
                    <!-- CONVERTER EM PDF -->
                    <div class="tools-grid" id="converter-em" style="display: none;">
                        <!-- JPG para PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">🖼️ JPG para PDF</h3>
                            <input type="file" id="jpgToPdf" accept=".jpg,.jpeg,.png" multiple class="file-input input-full">
                            <button onclick="convertJpgToPdf()" class="btn input-full">Converter para PDF</button>
                            <div class="loading" id="loadingJpgToPdf">Convertendo...</div>
                            <div class="result" id="resultJpgToPdf"></div>
                        </div>
                        <!-- WORD para PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">📝 WORD para PDF</h3>
                            <input type="file" id="wordToPdf" accept=".doc,.docx" class="file-input input-full">
                            <button onclick="convertWordToPdf()" class="btn input-full">Converter para PDF</button>
                            <div class="loading" id="loadingWordToPdf">Convertendo...</div>
                            <div class="result" id="resultWordToPdf"></div>
                        </div>
                        <!-- EXCEL para PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">📊 EXCEL para PDF</h3>
                            <input type="file" id="excelToPdf" accept=".xls,.xlsx" class="file-input input-full">
                            <button onclick="convertExcelToPdf()" class="btn input-full">Converter para PDF</button>
                            <div class="loading" id="loadingExcelToPdf">Convertendo...</div>
                            <div class="result" id="resultExcelToPdf"></div>
                        </div>
                        <!-- POWERPOINT para PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">📈 POWERPOINT para PDF</h3>
                            <input type="file" id="pptToPdf" accept=".ppt,.pptx" class="file-input input-full">
                            <button onclick="convertPptToPdf()" class="btn input-full">Converter para PDF</button>
                            <div class="loading" id="loadingPptToPdf">Convertendo...</div>
                            <div class="result" id="resultPptToPdf"></div>
                        </div>
                        <!-- HTML para PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">🌐 HTML para PDF</h3>
                            <input type="file" id="htmlToPdf" accept=".html,.htm" class="file-input input-full">
                            <button onclick="convertHtmlToPdf()" class="btn input-full">Converter para PDF</button>
                            <div class="loading" id="loadingHtmlToPdf">Convertendo...</div>
                            <div class="result" id="resultHtmlToPdf"></div>
                        </div>
                    </div>
                    <!-- CONVERTER DE PDF -->
                    <div class="tools-grid" id="converter-de" style="display: none;">
                        <div class="tool-card disabled"><h3>🖼️ PDF para JPG</h3><p>Em breve</p></div>
                        <div class="tool-card">
                            <h3>📝 PDF para WORD</h3>
                            <input type="file" id="pdfToWord" accept=".pdf" class="file-input">
                            <button onclick="convertToWord()" class="btn">Converter para DOCX</button>
                            <div class="loading" id="loadingWord">Convertendo...</div>
                            <div class="result" id="resultWord"></div>
                        </div>
                        <div class="tool-card">
                            <h3>📊 PDF para EXCEL</h3>
                            <input type="file" id="pdfToExcel" accept=".pdf" class="file-input">
                            <button onclick="convertToExcel()" class="btn">Converter para XLSX</button>
                            <div class="loading" id="loadingExcel">Convertendo...</div>
                            <div class="result" id="resultExcel"></div>
                        </div>
                        <div class="tool-card disabled"><h3>📈 PDF para POWERPOINT</h3><p>Em breve</p></div>
                        <div class="tool-card disabled"><h3>🅰️ PDF para PDF/A</h3><p>Em breve</p></div>
                    </div>
                    <!-- EDITAR PDF -->
                    <div class="tools-grid" id="editar" style="display: none;">
                        <!-- Rodar PDF (em breve) -->
                        <div class="tool-card disabled"><h3>🔄 Rodar PDF</h3><p>Em breve</p></div>
                        <!-- Inserir números de página (funcional) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">#️⃣ Inserir números de página</h3>
                            <input type="file" id="numberPdf" accept=".pdf" class="file-input input-full">
                            <button onclick="insertPageNumbers()" class="btn input-full">Inserir Números</button>
                            <div class="loading" id="loadingNumberPdf">Processando...</div>
                            <div class="result" id="resultNumberPdf"></div>
                        </div>
                        <!-- Inserir marca d'água (funcional) -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">💧 Inserir marca d'água</h3>
                            <input type="file" id="watermarkPdf" accept=".pdf" class="file-input input-full">
                            <input type="text" id="watermarkText" placeholder="Texto da marca d'água" class="input-full">
                            <button onclick="insertWatermark()" class="btn input-full">Inserir Marca d'Água</button>
                            <div class="loading" id="loadingWatermarkPdf">Processando...</div>
                            <div class="result" id="resultWatermarkPdf"></div>
                        </div>
                        <!-- Recortar PDF (em breve) -->
                        <div class="tool-card disabled"><h3>✂️ Recortar PDF</h3><p>Em breve</p></div>
                        <!-- Editar PDF (em breve) -->
                        <div class="tool-card disabled"><h3>✏️ Editar PDF</h3><p>Em breve</p></div>
                    </div>
                    <!-- SEGURANÇA DO PDF -->
                    <div class="tools-grid" id="seguranca" style="display: none;">
                        <!-- Desbloquear PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">🔓 Desbloquear PDF</h3>
                            <input type="file" id="unlockPdf" accept=".pdf" class="file-input input-full">
                            <input type="password" placeholder="Senha atual" id="unlockPassword" class="input-full">
                            <button onclick="unlockPdf()" class="btn input-full">Desbloquear PDF</button>
                            <div class="loading" id="loadingUnlockPdf">Desbloqueando...</div>
                            <div class="result" id="resultUnlockPdf"></div>
                        </div>
                        <!-- Proteger PDF -->
                        <div class="tool-card">
                            <h3 style="color: var(--lobios-purple)">🛡️ Proteger PDF</h3>
                            <input type="file" id="protectPdf" accept=".pdf" class="file-input input-full">
                            <input type="password" placeholder="Nova senha" id="protectPassword" class="input-full">
                            <button onclick="protectPdf()" class="btn input-full">Proteger PDF</button>
                            <div class="loading" id="loadingProtectPdf">Protegendo...</div>
                            <div class="result" id="resultProtectPdf"></div>
                        </div>
                        <!-- Outras funções -->
                        <div class="tool-card disabled"><h3>🖊️ Assinar PDF</h3><p>Em breve</p></div>
                        <div class="tool-card disabled"><h3>🙈 Ocultar PDF</h3><p>Em breve</p></div>
                        <div class="tool-card">
                            <h3>📋 Comparar PDF</h3>
                            <input type="file" id="comparePdf1" accept=".pdf" class="file-input input-full" placeholder="PDF 1">
                            <input type="file" id="comparePdf2" accept=".pdf" class="file-input input-full" placeholder="PDF 2">
                            <button onclick="comparePdfs()" class="btn input-full">Comparar Arquivos</button>
                            <div class="loading" id="loadingCompare">Comparando...</div>
                            <div class="result" id="resultCompare"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <!-- Botão Política de Privacidade -->
        <button id="privacyBtn" class="privacy-btn">Política de Privacidade</button>
        <!-- Modal Política -->
        <div id="privacyModal" class="modal-overlay">
            <div class="modal-content">
                <span id="closePrivacy" class="modal-close">&times;</span>
                <h2 style="color:var(--lobios-purple);margin:0 0 12px 0;font-size:2rem;font-weight:700;">Políticas de segurança e privacidade de dados</h2>
                <p style="margin-bottom:32px;color:var(--lobios-text);font-size:1.1rem;">Informações detalhadas sobre a estrutura de privacidade e segurança do PDF Platform Lobios.</p>
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:24px;">
                    <div style="background:rgba(123,50,148,0.05);border-radius:16px;padding:28px 20px;text-align:center;border:1px solid rgba(123,50,148,0.1);">
                        <div style="font-size:48px;margin-bottom:12px;">🔒</div>
                        <h4 style="color:var(--lobios-purple);margin:0 0 12px 0;font-size:1.2rem;font-weight:600;">Segurança</h4>
                        <p style="font-size:15px;color:var(--lobios-text);margin:0;line-height:1.6;">Todos os arquivos enviados são processados de forma segura e excluídos automaticamente após a conversão. Não armazenamos, visualizamos ou compartilhamos seus documentos.</p>
                    </div>
                    <div style="background:rgba(123,50,148,0.05);border-radius:16px;padding:28px 20px;text-align:center;border:1px solid rgba(123,50,148,0.1);">
                        <div style="font-size:48px;margin-bottom:12px;">🛡️</div>
                        <h4 style="color:var(--lobios-purple);margin:0 0 12px 0;font-size:1.2rem;font-weight:600;">Privacidade</h4>
                        <p style="font-size:15px;color:var(--lobios-text);margin:0;line-height:1.6;">Sua privacidade é prioridade. Os arquivos são eliminados dos nossos servidores logo após o processamento, garantindo total confidencialidade.</p>
                    </div>
                    <div style="background:rgba(123,50,148,0.05);border-radius:16px;padding:28px 20px;text-align:center;border:1px solid rgba(123,50,148,0.1);">
                        <div style="font-size:48px;margin-bottom:12px;">📄</div>
                        <h4 style="color:var(--lobios-purple);margin:0 0 12px 0;font-size:1.2rem;font-weight:600;">Termos</h4>
                        <p style="font-size:15px;color:var(--lobios-text);margin:0;line-height:1.6;">Ao utilizar o PDF Platform Lobios, você concorda com nossos termos: não armazenamos arquivos, não compartilhamos dados e não utilizamos seus documentos para nenhum outro fim.</p>
                    </div>
                    <div style="background:rgba(123,50,148,0.05);border-radius:16px;padding:28px 20px;text-align:center;border:1px solid rgba(123,50,148,0.1);">
                        <div style="font-size:48px;margin-bottom:12px;">🍪</div>
                        <h4 style="color:var(--lobios-purple);margin:0 0 12px 0;font-size:1.2rem;font-weight:600;">Cookies</h4>
                        <p style="font-size:15px;color:var(--lobios-text);margin:0;line-height:1.6;">Utilizamos apenas cookies essenciais para o funcionamento da plataforma. Não rastreamos, não vendemos e não utilizamos cookies para fins de marketing.</p>
                    </div>
                </div>
            </div>
        </div>
        <script>
            const API_BASE = '';

            function showLoading(id) {
                document.getElementById(`loading${id}`).style.display = 'block';
                document.getElementById(`result${id}`).style.display = 'none';
            }

            function hideLoading(id) {
                document.getElementById(`loading${id}`).style.display = 'none';
            }

            function showResult(id, message, isError = false) {
                const result = document.getElementById(`result${id}`);
                result.innerHTML = message;
                result.className = isError ? 'result error' : 'result';
                result.style.display = 'block';
            }

            async function convertToWord() {
                const file = document.getElementById('pdfToWord').files[0];
                if (!file) return alert('Selecione um arquivo PDF');

                showLoading('Word');
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/convert/word', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        showResult('Word', `<a href="${url}" download="${file.name.replace('.pdf', '.docx')}">📥 Download DOCX</a>`);
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    showResult('Word', 'Erro ao converter arquivo', true);
                } finally {
                    hideLoading('Word');
                }
            }

            async function convertToExcel() {
                const file = document.getElementById('pdfToExcel').files[0];
                if (!file) return alert('Selecione um arquivo PDF');

                showLoading('Excel');
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/convert/excel', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        showResult('Excel', `<a href="${url}" download="${file.name.replace('.pdf', '.xlsx')}">📥 Download XLSX</a>`);
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    showResult('Excel', 'Erro ao converter arquivo', true);
                } finally {
                    hideLoading('Excel');
                }
            }

            async function mergePdfs() {
                const files = document.getElementById('mergePdfs').files;
                if (files.length < 2) return alert('Selecione pelo menos 2 arquivos PDF');

                showLoading('Merge');
                const formData = new FormData();
                for (let file of files) {
                    formData.append('files', file);
                }

                try {
                    const response = await fetch('/merge', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        showResult('Merge', `<a href="${url}" download="merged.pdf">📥 Download PDF Combinado</a>`);
                    } else {
                        throw new Error('Erro ao juntar arquivos');
                    }
                } catch (error) {
                    showResult('Merge', 'Erro ao juntar arquivos', true);
                } finally {
                    hideLoading('Merge');
                }
            }

            async function splitPdf() {
                const file = document.getElementById('splitPdf').files[0];
                const startPage = document.getElementById('startPage').value;
                const endPage = document.getElementById('endPage').value;

                if (!file) return alert('Selecione um arquivo PDF');
                if (!startPage || !endPage) return alert('Informe as páginas inicial e final');

                showLoading('Split');
                const formData = new FormData();
                formData.append('file', file);
                formData.append('start_page', startPage);
                formData.append('end_page', endPage);

                try {
                    const response = await fetch('/split', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        showResult('Split', `<a href="${url}" download="extracted_pages.pdf">📥 Download Páginas Extraídas</a>`);
                    } else {
                        throw new Error('Erro ao extrair páginas');
                    }
                } catch (error) {
                    showResult('Split', 'Erro ao extrair páginas', true);
                } finally {
                    hideLoading('Split');
                }
            }

            async function compressPdf() {
                const file = document.getElementById('compressPdf').files[0];
                if (!file) return alert('Selecione um arquivo PDF');

                showLoading('Compress');
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch('/compress', {
                        method: 'POST',
                        body: formData
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        showResult('Compress', `<a href="${url}" download="${file.name.replace('.pdf', '_compressed.pdf')}">📥 Download PDF Comprimido</a>`);
                    } else {
                        throw new Error('Erro ao comprimir');
                    }
                } catch (error) {
                    showResult('Compress', 'Erro ao comprimir arquivo', true);
                } finally {
                    hideLoading('Compress');
                }
            }

            async function comparePdfs() {
                const file1 = document.getElementById('comparePdf1').files[0];
                const file2 = document.getElementById('comparePdf2').files[0];

                if (!file1 || !file2) return alert('Selecione os dois arquivos PDF');

                showLoading('Compare');
                const formData = new FormData();
                formData.append('file1', file1);
                formData.append('file2', file2);

                try {
                    const response = await fetch('/compare', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();
                    if (response.ok) {
                        showResult('Compare', result.message);
                    } else {
                        throw new Error(result.detail);
                    }
                } catch (error) {
                    showResult('Compare', 'Erro ao comparar arquivos', true);
                } finally {
                    hideLoading('Compare');
                }
            }

            async function removePages() {
                const file = document.getElementById('removePagesPdf').files[0];
                const pages = document.getElementById('removePagesList').value;
                if (!file || !pages) return alert('Selecione o PDF e informe as páginas a remover');
                document.getElementById('loadingRemovePages').style.display = 'block';
                document.getElementById('resultRemovePages').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                formData.append('pages', pages);
                try {
                    const response = await fetch('/remove-pages', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultRemovePages').innerHTML = `<a href="${url}" download="removed_pages.pdf">📥 Download PDF sem páginas</a>`;
                        document.getElementById('resultRemovePages').className = 'result';
                    } else {
                        throw new Error('Erro ao remover páginas');
                    }
                } catch (error) {
                    document.getElementById('resultRemovePages').innerHTML = 'Erro ao remover páginas';
                    document.getElementById('resultRemovePages').className = 'result error';
                } finally {
                    document.getElementById('loadingRemovePages').style.display = 'none';
                    document.getElementById('resultRemovePages').style.display = 'block';
                }
            }
            async function extractPages() {
                const file = document.getElementById('extractPagesPdf').files[0];
                const pages = document.getElementById('extractPagesList').value;
                if (!file || !pages) return alert('Selecione o PDF e informe as páginas a extrair');
                document.getElementById('loadingExtractPages').style.display = 'block';
                document.getElementById('resultExtractPages').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                formData.append('pages', pages);
                try {
                    const response = await fetch('/extract-pages', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultExtractPages').innerHTML = `<a href="${url}" download="extracted_pages.pdf">📥 Download Páginas Extraídas</a>`;
                        document.getElementById('resultExtractPages').className = 'result';
                    } else {
                        throw new Error('Erro ao extrair páginas');
                    }
                } catch (error) {
                    document.getElementById('resultExtractPages').innerHTML = 'Erro ao extrair páginas';
                    document.getElementById('resultExtractPages').className = 'result error';
                } finally {
                    document.getElementById('loadingExtractPages').style.display = 'none';
                    document.getElementById('resultExtractPages').style.display = 'block';
                }
            }
            async function organizePdfPages() {
                const file = document.getElementById('organizePdf').files[0];
                const order = document.getElementById('organizeOrder').value;
                if (!file || !order) return alert('Selecione o PDF e informe a nova ordem das páginas');
                document.getElementById('loadingOrganizePdf').style.display = 'block';
                document.getElementById('resultOrganizePdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                formData.append('order', order);
                try {
                    const response = await fetch('/organize-pages', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultOrganizePdf').innerHTML = `<a href="${url}" download="organized.pdf">📥 Download PDF Organizado</a>`;
                        document.getElementById('resultOrganizePdf').className = 'result';
                    } else {
                        throw new Error('Erro ao organizar páginas');
                    }
                } catch (error) {
                    document.getElementById('resultOrganizePdf').innerHTML = 'Erro ao organizar páginas';
                    document.getElementById('resultOrganizePdf').className = 'result error';
                } finally {
                    document.getElementById('loadingOrganizePdf').style.display = 'none';
                    document.getElementById('resultOrganizePdf').style.display = 'block';
                }
            }

            async function convertJpgToPdf() {
                const files = document.getElementById('jpgToPdf').files;
                if (!files.length) return alert('Selecione pelo menos uma imagem');
                document.getElementById('loadingJpgToPdf').style.display = 'block';
                document.getElementById('resultJpgToPdf').style.display = 'none';
                const formData = new FormData();
                for (let file of files) formData.append('files', file);
                try {
                    const response = await fetch('/convert/jpg-to-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultJpgToPdf').innerHTML = `<a href="${url}" download="imagens.pdf">📥 Download PDF</a>`;
                        document.getElementById('resultJpgToPdf').className = 'result';
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    document.getElementById('resultJpgToPdf').innerHTML = 'Erro ao converter';
                    document.getElementById('resultJpgToPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingJpgToPdf').style.display = 'none';
                    document.getElementById('resultJpgToPdf').style.display = 'block';
                }
            }
            async function convertWordToPdf() {
                const file = document.getElementById('wordToPdf').files[0];
                if (!file) return alert('Selecione um arquivo Word');
                document.getElementById('loadingWordToPdf').style.display = 'block';
                document.getElementById('resultWordToPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const response = await fetch('/convert/word-to-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultWordToPdf').innerHTML = `<a href="${url}" download="${file.name.replace(/\.[^.]+$/, '.pdf')}">📥 Download PDF</a>`;
                        document.getElementById('resultWordToPdf').className = 'result';
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    document.getElementById('resultWordToPdf').innerHTML = 'Erro ao converter';
                    document.getElementById('resultWordToPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingWordToPdf').style.display = 'none';
                    document.getElementById('resultWordToPdf').style.display = 'block';
                }
            }
            async function convertExcelToPdf() {
                const file = document.getElementById('excelToPdf').files[0];
                if (!file) return alert('Selecione um arquivo Excel');
                document.getElementById('loadingExcelToPdf').style.display = 'block';
                document.getElementById('resultExcelToPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const response = await fetch('/convert/excel-to-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultExcelToPdf').innerHTML = `<a href="${url}" download="${file.name.replace(/\.[^.]+$/, '.pdf')}">📥 Download PDF</a>`;
                        document.getElementById('resultExcelToPdf').className = 'result';
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    document.getElementById('resultExcelToPdf').innerHTML = 'Erro ao converter';
                    document.getElementById('resultExcelToPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingExcelToPdf').style.display = 'none';
                    document.getElementById('resultExcelToPdf').style.display = 'block';
                }
            }
            async function convertPptToPdf() {
                const file = document.getElementById('pptToPdf').files[0];
                if (!file) return alert('Selecione um arquivo PowerPoint');
                document.getElementById('loadingPptToPdf').style.display = 'block';
                document.getElementById('resultPptToPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const response = await fetch('/convert/ppt-to-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultPptToPdf').innerHTML = `<a href="${url}" download="${file.name.replace(/\.[^.]+$/, '.pdf')}">📥 Download PDF</a>`;
                        document.getElementById('resultPptToPdf').className = 'result';
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    document.getElementById('resultPptToPdf').innerHTML = 'Erro ao converter';
                    document.getElementById('resultPptToPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingPptToPdf').style.display = 'none';
                    document.getElementById('resultPptToPdf').style.display = 'block';
                }
            }
            async function convertHtmlToPdf() {
                const file = document.getElementById('htmlToPdf').files[0];
                if (!file) return alert('Selecione um arquivo HTML');
                document.getElementById('loadingHtmlToPdf').style.display = 'block';
                document.getElementById('resultHtmlToPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const response = await fetch('/convert/html-to-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultHtmlToPdf').innerHTML = `<a href="${url}" download="${file.name.replace(/\.[^.]+$/, '.pdf')}">📥 Download PDF</a>`;
                        document.getElementById('resultHtmlToPdf').className = 'result';
                    } else {
                        throw new Error('Erro na conversão');
                    }
                } catch (error) {
                    document.getElementById('resultHtmlToPdf').innerHTML = 'Erro ao converter';
                    document.getElementById('resultHtmlToPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingHtmlToPdf').style.display = 'none';
                    document.getElementById('resultHtmlToPdf').style.display = 'block';
                }
            }

            async function unlockPdf() {
                const file = document.getElementById('unlockPdf').files[0];
                const password = document.getElementById('unlockPassword').value;
                if (!file || !password) return alert('Selecione o PDF e informe a senha');
                document.getElementById('loadingUnlockPdf').style.display = 'block';
                document.getElementById('resultUnlockPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                formData.append('password', password);
                try {
                    const response = await fetch('/unlock-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultUnlockPdf').innerHTML = `<a href="${url}" download="unlocked.pdf">📥 Download PDF Desbloqueado</a>`;
                        document.getElementById('resultUnlockPdf').className = 'result';
                    } else {
                        throw new Error('Erro ao desbloquear');
                    }
                } catch (error) {
                    document.getElementById('resultUnlockPdf').innerHTML = 'Erro ao desbloquear PDF';
                    document.getElementById('resultUnlockPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingUnlockPdf').style.display = 'none';
                    document.getElementById('resultUnlockPdf').style.display = 'block';
                }
            }
            async function protectPdf() {
                const file = document.getElementById('protectPdf').files[0];
                const password = document.getElementById('protectPassword').value;
                if (!file || !password) return alert('Selecione o PDF e informe a nova senha');
                document.getElementById('loadingProtectPdf').style.display = 'block';
                document.getElementById('resultProtectPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                formData.append('password', password);
                try {
                    const response = await fetch('/protect-pdf', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultProtectPdf').innerHTML = `<a href="${url}" download="protected.pdf">📥 Download PDF Protegido</a>`;
                        document.getElementById('resultProtectPdf').className = 'result';
                    } else {
                        throw new Error('Erro ao proteger');
                    }
                } catch (error) {
                    document.getElementById('resultProtectPdf').innerHTML = 'Erro ao proteger PDF';
                    document.getElementById('resultProtectPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingProtectPdf').style.display = 'none';
                    document.getElementById('resultProtectPdf').style.display = 'block';
                }
            }

            async function insertPageNumbers() {
                const file = document.getElementById('numberPdf').files[0];
                if (!file) return alert('Selecione um PDF');
                document.getElementById('loadingNumberPdf').style.display = 'block';
                document.getElementById('resultNumberPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                try {
                    const response = await fetch('/edit/add-page-numbers', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultNumberPdf').innerHTML = `<a href="${url}" download="numbered.pdf">📥 Download PDF Numerado</a>`;
                        document.getElementById('resultNumberPdf').className = 'result';
                    } else {
                        throw new Error('Erro ao inserir números');
                    }
                } catch (error) {
                    document.getElementById('resultNumberPdf').innerHTML = 'Erro ao inserir números';
                    document.getElementById('resultNumberPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingNumberPdf').style.display = 'none';
                    document.getElementById('resultNumberPdf').style.display = 'block';
                }
            }
            async function insertWatermark() {
                const file = document.getElementById('watermarkPdf').files[0];
                const text = document.getElementById('watermarkText').value;
                if (!file || !text) return alert('Selecione o PDF e informe o texto da marca d\'água');
                document.getElementById('loadingWatermarkPdf').style.display = 'block';
                document.getElementById('resultWatermarkPdf').style.display = 'none';
                const formData = new FormData();
                formData.append('file', file);
                formData.append('text', text);
                try {
                    const response = await fetch('/edit/add-watermark', { method: 'POST', body: formData });
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        document.getElementById('resultWatermarkPdf').innerHTML = `<a href="${url}" download="watermarked.pdf">📥 Download PDF com Marca d'Água</a>`;
                        document.getElementById('resultWatermarkPdf').className = 'result';
                    } else {
                        throw new Error('Erro ao inserir marca d\'água');
                    }
                } catch (error) {
                    document.getElementById('resultWatermarkPdf').innerHTML = 'Erro ao inserir marca d\'água';
                    document.getElementById('resultWatermarkPdf').className = 'result error';
                } finally {
                    document.getElementById('loadingWatermarkPdf').style.display = 'none';
                    document.getElementById('resultWatermarkPdf').style.display = 'block';
                }
            }

            // Alternar categorias na barra lateral
            document.querySelectorAll('.category-link').forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    document.querySelectorAll('.category-link').forEach(l => l.classList.remove('active'));
                    this.classList.add('active');
                    // Esconde todas as grids
                    document.querySelectorAll('.tools-grid').forEach(grid => grid.style.display = 'none');
                    // Mostra a grid da categoria
                    const cat = this.getAttribute('data-category');
                    document.getElementById(cat).style.display = 'grid';
                    // Atualiza título
                    document.getElementById('category-title').textContent = this.textContent;
                    // Atualiza descrição
                    let desc = '';
                    switch(cat) {
                        case 'organizar': desc = 'Manipule e organize seus arquivos PDF.'; break;
                        case 'otimizar': desc = 'Otimize e melhore seus PDFs.'; break;
                        case 'converter-em': desc = 'Converta outros formatos em PDF.'; break;
                        case 'converter-de': desc = 'Converta PDF para outros formatos.'; break;
                        case 'editar': desc = 'Edite e personalize seus PDFs.'; break;
                        case 'seguranca': desc = 'Proteja e gerencie a segurança dos seus PDFs.'; break;
                        default: desc = 'Manipule seus arquivos PDF facilmente';
                    }
                    document.getElementById('category-desc').textContent = desc;
                });
            });
        </script>
        <script src="/static/app.js"></script>
    </body>
    </html>
    """

@app.post("/convert/word")
async def convert_to_word(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    # Verificar se a chave está configurada (tentar ler novamente)
    secret = get_convertapi_secret()
    if not secret:
        raise HTTPException(
            status_code=500, 
            detail="CONVERTAPI_SECRET não configurada. Verifique se a variável de ambiente está configurada no Railway e faça um redeploy."
        )
    
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📝 <b>PDF para Word</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    # Salvar arquivo temporário
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Verificar se o arquivo foi salvo corretamente
        if not os.path.exists(temp_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar arquivo temporário")
        
        # Verificar tamanho do arquivo
        file_size = os.path.getsize(temp_path)
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Arquivo PDF está vazio")
        
        # Converter PDF para DOCX usando ConvertAPI
        print(f"Tentando converter PDF para DOCX. Tamanho: {file_size} bytes")
        print(f"Chave ConvertAPI configurada: {'Sim' if secret else 'Não'}")
        print(f"Caminho do arquivo: {temp_path}")
        
        # Usar a sintaxe correta da ConvertAPI
        result = convertapi.convert('docx', {
            'File': temp_path
        }, from_format='pdf')
        
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_converted.docx"
        result.file.save(output_path)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar arquivo convertido")
        
        return FileResponse(output_path, filename=file.filename.replace('.pdf', '.docx'))
    
    except convertapi.ApiError as e:
        error_msg = f"Erro na ConvertAPI: {str(e)}"
        if "secret" in str(e).lower() or "api" in str(e).lower() or "authentication" in str(e).lower():
            error_msg = "Erro de autenticação na ConvertAPI. Verifique se CONVERTAPI_SECRET está configurada corretamente no Railway."
        elif "file" in str(e).lower() or "format" in str(e).lower():
            error_msg = f"Erro ao processar arquivo: {str(e)}"
        print(f"ConvertAPI Error: {str(e)}")
        raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_type = type(e).__name__
        error_detail = f"Erro inesperado ({error_type}): {str(e)}"
        
        # Log completo para debug
        print(f"=== ERRO DETALHADO ===")
        print(f"Tipo: {error_type}")
        print(f"Mensagem: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        print(f"=====================")
        
        # Retornar mensagem mais útil para o usuário
        if "secret" in str(e).lower() or "api_secret" in str(e).lower():
            error_detail = "CONVERTAPI_SECRET não configurada ou inválida. Verifique as variáveis de ambiente no Railway."
        elif "file" in str(e).lower() or "path" in str(e).lower():
            error_detail = f"Erro ao processar arquivo: {str(e)}"
        
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        # Limpar arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/convert/excel")
async def convert_to_excel(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    # Verificar se a chave está configurada (tentar ler novamente)
    secret = get_convertapi_secret()
    if not secret:
        raise HTTPException(
            status_code=500, 
            detail="CONVERTAPI_SECRET não configurada. Verifique se a variável de ambiente está configurada no Railway e faça um redeploy."
        )
    
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📊 <b>PDF para Excel</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Converter PDF para XLSX usando ConvertAPI
        result = convertapi.convert('xlsx', {
            'File': temp_path
        }, from_format='pdf')
        
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_converted.xlsx"
        result.file.save(output_path)
        
        return FileResponse(output_path, filename=file.filename.replace('.pdf', '.xlsx'))
    
    except Exception as e:
        import traceback
        error_detail = f"Erro na conversão: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/merge")
async def merge_pdfs(request: Request, files: List[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Necessário pelo menos 2 arquivos")
    
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🧩 <b>Juntar PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>\nArquivos: {len(files)}")

    temp_paths = []
    try:
        # Salvar arquivos temporários
        for file in files:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Todos os arquivos devem ser PDF")
            
            temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_paths.append(temp_path)
        
        # Nota: ConvertAPI não tem suporte direto para merge de múltiplos PDFs
        # Usando pypdf para esta funcionalidade específica (merge é uma operação simples)
        import pypdf
        
        merger = pypdf.PdfWriter()
        for path in temp_paths:
            reader = pypdf.PdfReader(path)
            for page in reader.pages:
                merger.add_page(page)
        
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_merged.pdf"
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF mesclado")
        
        return FileResponse(output_path, filename="merged.pdf")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_type = type(e).__name__
        error_detail = f"Erro ao juntar PDFs ({error_type}): {str(e)}"
        
        print(f"=== ERRO DETALHADO MERGE ===")
        print(f"Tipo: {error_type}")
        print(f"Mensagem: {str(e)}")
        print(f"Traceback:\n{error_trace}")
        print(f"============================")
        
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        # Limpar arquivos temporários
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)

@app.post("/split")
async def split_pdf(request: Request, file: UploadFile = File(...), start_page: int = Form(...), end_page: int = Form(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"✂️ <b>Dividir PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Nota: ConvertAPI pode não suportar PageRange diretamente
        # Usando pypdf para dividir PDF (operação simples)
        import pypdf
        
        reader = pypdf.PdfReader(temp_path)
        total_pages = len(reader.pages)
        
        if start_page < 1 or end_page > total_pages or start_page > end_page:
            raise HTTPException(status_code=400, detail=f"Páginas inválidas. PDF tem {total_pages} páginas.")
            
            writer = pypdf.PdfWriter()
            for i in range(start_page - 1, end_page):
                writer.add_page(reader.pages[i])
            
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_extracted.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF extraído")
            
            return FileResponse(output_path, filename="extracted_pages.pdf")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao dividir PDF: {str(e)}"
        print(f"Erro ao dividir PDF: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/compress")
async def compress_pdf(request: Request, file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🗜️ <b>Comprimir PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Nota: ConvertAPI não comprime PDF diretamente
        # Usando pypdf para comprimir (remove objetos duplicados e otimiza)
        import pypdf
        
        reader = pypdf.PdfReader(temp_path)
        writer = pypdf.PdfWriter()
        
        for page in reader.pages:
            writer.add_page(page)
        
        # Compressão básica - remove objetos duplicados
        writer.compress_identical_objects()
        
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_compressed.pdf"
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF comprimido")
        
        return FileResponse(output_path, filename=file.filename.replace('.pdf', '_compressed.pdf'))
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao comprimir PDF: {str(e)}"
        print(f"Erro ao comprimir PDF: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/compare")
async def compare_pdfs(request: Request, file1: UploadFile = File(...), file2: UploadFile = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📋 <b>Comparar PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_paths = []
    try:
        # Salvar arquivos temporários
        for file in [file1, file2]:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail="Arquivos devem ser PDF")
            
            temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            temp_paths.append(temp_path)
        
        # Extrair texto dos PDFs
        texts = []
        page_counts = []
        
        for path in temp_paths:
            with open(path, 'rb') as pdf_file:
                reader = pypdf.PdfReader(pdf_file)
                page_counts.append(len(reader.pages))
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                texts.append(text)
        
        # Comparação básica
        similarity = len(set(texts[0].split()) & set(texts[1].split())) / len(set(texts[0].split()) | set(texts[1].split())) * 100
        
        return {
            "message": f"📊 Comparação concluída:<br>• Arquivo 1: {page_counts[0]} páginas<br>• Arquivo 2: {page_counts[1]} páginas<br>• Similaridade: {similarity:.1f}%"
        }
    
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)

# NOVOS ENDPOINTS FASTAPI
@app.post("/remove-pages")
async def remove_pages(request: Request, file: UploadFile = File(...), pages: str = Form(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"❌ <b>Remover páginas</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>\nPáginas: {pages}")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Parse páginas a remover e criar range de páginas a manter
            remove_set = set()
            for part in pages.split(','):
            part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    remove_set.update(range(start, end+1))
                else:
                    remove_set.add(int(part))
        
        # Nota: ConvertAPI não tem função direta de remover páginas específicas
        # Usando pypdf para esta funcionalidade específica
        import pypdf
        with open(temp_path, 'rb') as pdf_file:
            reader = pypdf.PdfReader(pdf_file)
            writer = pypdf.PdfWriter()
            total = len(reader.pages)
            for i in range(total):
                if (i+1) not in remove_set:
                    writer.add_page(reader.pages[i])
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_removed.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            return FileResponse(output_path, filename="removed_pages.pdf")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover páginas: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/extract-pages")
async def extract_pages(request: Request, file: UploadFile = File(...), pages: str = Form(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📤 <b>Extrair páginas</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>\nPáginas: {pages}")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Nota: ConvertAPI pode não suportar PageRange diretamente
        # Usando pypdf para extrair páginas (operação simples)
        import pypdf
        
        # Parse páginas a extrair
            extract_set = set()
            for part in pages.split(','):
            part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    extract_set.update(range(start, end+1))
                else:
                    extract_set.add(int(part))
        
        reader = pypdf.PdfReader(temp_path)
        total_pages = len(reader.pages)
        
        # Validar páginas
        invalid_pages = [p for p in extract_set if p < 1 or p > total_pages]
        if invalid_pages:
            raise HTTPException(status_code=400, detail=f"Páginas inválidas: {invalid_pages}. PDF tem {total_pages} páginas.")
        
        writer = pypdf.PdfWriter()
        sorted_pages = sorted(extract_set)
        for page_num in sorted_pages:
            if 1 <= page_num <= total_pages:
                writer.add_page(reader.pages[page_num - 1])
        
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_extracted.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF extraído")
        
            return FileResponse(output_path, filename="extracted_pages.pdf")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao extrair páginas: {str(e)}"
        print(f"Erro ao extrair páginas: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/organize-pages")
async def organize_pages(request: Request, file: UploadFile = File(...), order: str = Form(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🔀 <b>Organizar PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>\nOrdem: {order}")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Nota: ConvertAPI não tem função direta de reorganizar páginas
        # Usando pypdf para organizar páginas (extrair e juntar na ordem desejada)
        import pypdf
        
        reader = pypdf.PdfReader(temp_path)
            total = len(reader.pages)
            order_list = [int(x) for x in order.split(',') if x.strip().isdigit()]
        
        # Validar ordem
        invalid_pages = [p for p in order_list if p < 1 or p > total]
        if invalid_pages:
            raise HTTPException(status_code=400, detail=f"Páginas inválidas na ordem: {invalid_pages}. PDF tem {total} páginas.")
        
        writer = pypdf.PdfWriter()
            for idx in order_list:
                if 1 <= idx <= total:
                writer.add_page(reader.pages[idx - 1])
        
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_organized.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF organizado")
        
            return FileResponse(output_path, filename="organized.pdf")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao organizar páginas: {str(e)}"
        print(f"Erro ao organizar páginas: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# NOVOS ENDPOINTS CONVERTER EM PDF
@app.post("/convert/jpg-to-pdf")
async def jpg_to_pdf(request: Request, files: list[UploadFile] = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🖼️ <b>JPG para PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>\nArquivos: {len(files)}")

    temp_paths = []
    try:
        # Salvar arquivos temporários
    for file in files:
        temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        temp_paths.append(temp_path)
        
        # Se houver múltiplas imagens, usar merge. Se uma só, converter diretamente
        if len(temp_paths) == 1:
            result = convertapi.convert('pdf', {
                'File': temp_paths[0]
            }, from_format='jpg')
        else:
            # Para múltiplas imagens, converter cada uma e depois juntar
            pdf_paths = []
            for img_path in temp_paths:
                result = convertapi.convert('pdf', {
                    'File': img_path
                }, from_format='jpg')
                pdf_temp = f"{OUTPUT_DIR}/{uuid.uuid4()}_temp.pdf"
                result.file.save(pdf_temp)
                pdf_paths.append(pdf_temp)
            
            # Juntar os PDFs usando pypdf (ConvertAPI não suporta merge direto)
            import pypdf
            merger = pypdf.PdfWriter()
            for pdf_path in pdf_paths:
                reader = pypdf.PdfReader(pdf_path)
                for page in reader.pages:
                    merger.add_page(page)
            
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_jpg2pdf.pdf"
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            
            # Limpar PDFs temporários
            for path in pdf_paths:
                if os.path.exists(path):
                    os.remove(path)
            
    return FileResponse(output_path, filename="imagens.pdf")
        
        # Se chegou aqui, é uma única imagem
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_jpg2pdf.pdf"
        result.file.save(output_path)
        
        return FileResponse(output_path, filename="imagens.pdf")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter imagens: {str(e)}")
    finally:
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)

@app.post("/convert/word-to-pdf")
async def word_to_pdf(request: Request, file: UploadFile = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📝 <b>Word para PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Converter Word para PDF usando ConvertAPI
        result = convertapi.convert('pdf', {
            'File': temp_path
        }, from_format='docx' if file.filename.endswith('.docx') else 'doc')
        
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_word2pdf.pdf"
        result.file.save(output_path)
        
    return FileResponse(output_path, filename=file.filename.replace('.docx', '.pdf').replace('.doc', '.pdf'))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter Word: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/convert/excel-to-pdf")
async def excel_to_pdf(request: Request, file: UploadFile = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📊 <b>Excel para PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Converter Excel para PDF usando ConvertAPI
        result = convertapi.convert('pdf', {
            'File': temp_path
        }, from_format='xlsx' if file.filename.endswith('.xlsx') else 'xls')
        
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_excel2pdf.pdf"
        result.file.save(output_path)
        
    return FileResponse(output_path, filename=file.filename.replace('.xlsx', '.pdf').replace('.xls', '.pdf'))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter Excel: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/convert/ppt-to-pdf")
async def ppt_to_pdf(request: Request, file: UploadFile = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"📈 <b>PowerPoint para PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Converter PowerPoint para PDF usando ConvertAPI
        result = convertapi.convert('pdf', {
            'File': temp_path
        }, from_format='pptx' if file.filename.endswith('.pptx') else 'ppt')
        
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_ppt2pdf.pdf"
        result.file.save(output_path)
        
    return FileResponse(output_path, filename=file.filename.replace('.pptx', '.pdf').replace('.ppt', '.pdf'))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter PowerPoint: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/convert/html-to-pdf")
async def html_to_pdf(request: Request, file: UploadFile = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🌐 <b>HTML para PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Converter HTML para PDF usando ConvertAPI
        result = convertapi.convert('pdf', {
            'File': temp_path
        }, from_format='html')
        
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_html2pdf.pdf"
        result.file.save(output_path)
        
    return FileResponse(output_path, filename=file.filename.replace('.html', '.pdf').replace('.htm', '.pdf'))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao converter HTML: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ENDPOINTS SEGURANÇA DO PDF
@app.post("/unlock-pdf")
async def unlock_pdf(request: Request, file: UploadFile = File(...), password: str = Form(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🔓 <b>Desbloquear PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Nota: ConvertAPI pode não suportar desbloquear PDF diretamente
        # Usando pypdf para desbloquear (lê com senha e salva sem senha)
        import pypdf
        
        reader = pypdf.PdfReader(temp_path, password=password)
            writer = pypdf.PdfWriter()
        
            for page in reader.pages:
                writer.add_page(page)
        
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_unlocked.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF desbloqueado")
        
            return FileResponse(output_path, filename="unlocked.pdf")
    
    except pypdf.errors.PdfReadError as e:
        if "password" in str(e).lower():
            raise HTTPException(status_code=400, detail="Senha incorreta")
        raise HTTPException(status_code=500, detail=f"Erro ao ler PDF: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao desbloquear PDF: {str(e)}"
        print(f"Erro ao desbloquear PDF: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/protect-pdf")
async def protect_pdf(request: Request, file: UploadFile = File(...), password: str = Form(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"🛡️ <b>Proteger PDF</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Nota: ConvertAPI pode não suportar proteger PDF diretamente
        # Usando pypdf para proteger (criptografa com senha)
        import pypdf
        
        reader = pypdf.PdfReader(temp_path)
            writer = pypdf.PdfWriter()
        
            for page in reader.pages:
                writer.add_page(page)
        
        # Criptografar com senha
            writer.encrypt(password)
        
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_protected.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
        
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="Erro ao salvar PDF protegido")
        
            return FileResponse(output_path, filename="protected.pdf")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"Erro ao proteger PDF: {str(e)}"
        print(f"Erro ao proteger PDF: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# ENDPOINTS EDITAR PDF
@app.post("/edit/add-page-numbers")
async def add_page_numbers(request: Request, file: UploadFile = File(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"#️⃣ <b>Inserir números de página</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>")

    # Nota: ConvertAPI não tem suporte direto para inserir números de página
    # Usando pypdf e reportlab para esta funcionalidade específica
    import pypdf
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io
    
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_numbered.pdf"
    try:
        reader = pypdf.PdfReader(temp_path)
        writer = pypdf.PdfWriter()
        for i, page in enumerate(reader.pages):
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            can.setFont("Helvetica", 10)
            can.drawString(500, 20, f"{i+1}")
            can.save()
            packet.seek(0)
            watermark_reader = pypdf.PdfReader(packet)
            page.merge_page(watermark_reader.pages[0])
            writer.add_page(page)
        with open(output_path, 'wb') as f:
            writer.write(f)
        return FileResponse(output_path, filename="numbered.pdf")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inserir números: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/edit/add-watermark")
async def add_watermark(request: Request, file: UploadFile = File(...), text: str = Form(...)):
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "N/A")
    country = get_country_from_ip(ip)
    notify_telegram(f"💧 <b>Inserir marca d'água</b>\nIP: <code>{ip}</code> ({country})\nUA: <code>{user_agent}</code>\nTexto: {text}")

    # Nota: ConvertAPI não tem suporte direto para inserir marca d'água
    # Usando pypdf e reportlab para esta funcionalidade específica
    import pypdf
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io
    
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_watermarked.pdf"
    try:
        reader = pypdf.PdfReader(temp_path)
        writer = pypdf.PdfWriter()
        for page in reader.pages:
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)
            can.setFont("Helvetica", 16)
            can.setFillColorRGB(0.7, 0.7, 0.7)
            can.saveState()
            can.translate(300, 400)
            can.rotate(30)
            can.drawCentredString(0, 0, text)
            can.restoreState()
            can.save()
            packet.seek(0)
            watermark_reader = pypdf.PdfReader(packet)
            page.merge_page(watermark_reader.pages[0])
            writer.add_page(page)
        with open(output_path, 'wb') as f:
            writer.write(f)
        return FileResponse(output_path, filename="watermarked.pdf")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inserir marca d'água: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)