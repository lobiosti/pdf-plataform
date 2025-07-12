from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
import pypdf
from docx import Document
from openpyxl import Workbook
import tempfile
import zipfile
from typing import List
import uuid

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
        <style>
            :root {
                --lobios-purple: #7b3294;
                --lobios-purple-light: #a259c6;
                --lobios-bg: #f8f8fa;
                --lobios-card: #fff;
                --lobios-gray: #e5e5e5;
                --lobios-dark: #222;
            }
            body {
                margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif;
                background: var(--lobios-bg);
                color: var(--lobios-dark);
            }
            .sidebar {
                position: fixed; left: 0; top: 0; bottom: 0; width: 220px; background: #fff;
                color: var(--lobios-purple); display: flex; flex-direction: column; align-items: center; padding-top: 30px; z-index: 2; border-right: 1.5px solid #eee;
            }
            .sidebar img {
                width: 140px; margin-bottom: 30px; filter: none;
            }
            .sidebar nav {
                width: 100%;
            }
            .sidebar nav a {
                display: block; color: var(--lobios-purple); text-decoration: none; padding: 14px 30px; font-size: 16px;
                border-left: 4px solid transparent; transition: background 0.2s, border 0.2s; font-weight: 500;
            }
            .sidebar nav a.active, .sidebar nav a:hover {
                background: #f3eafd; border-left: 4px solid var(--lobios-purple);
                color: var(--lobios-purple);
            }
            .main {
                margin-left: 220px; min-height: 100vh;
            }
            .topbar {
                background: #fff; height: 64px; display: flex; align-items: center; justify-content: flex-end;
                box-shadow: 0 2px 8px rgba(123,50,148,0.07); padding: 0 40px; position: sticky; top: 0; z-index: 1;
            }
            .topbar .user {
                font-weight: 500; color: var(--lobios-purple); display: flex; align-items: center;
            }
            .topbar .user:before {
                content: '\1F464'; font-size: 22px; margin-right: 8px;
            }
            .container {
                max-width: 1200px; margin: 30px auto; padding: 0 20px;
            }
            .header h1 {
                color: var(--lobios-purple); margin-bottom: 10px; font-size: 2.2rem;
            }
            .tools-grid {
                display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px;
            }
            .tool-card {
                background: var(--lobios-card); border-radius: 12px; padding: 28px 22px; box-shadow: 0 2px 12px rgba(123,50,148,0.08);
                display: flex; flex-direction: column; align-items: stretch;
            }
            .tool-card h3 {
                color: var(--lobios-purple); margin-bottom: 18px; font-size: 19px; font-weight: 600;
            }
            .file-input { width: 100%; padding: 10px; border: 2px dashed var(--lobios-purple-light); border-radius: 6px; margin-bottom: 15px; cursor: pointer; background: #faf7fc; }
            .file-input:hover { border-color: var(--lobios-purple); }
            .btn { background: var(--lobios-purple); color: white; border: none; padding: 13px 0; border-radius: 6px; cursor: pointer; width: 100%; font-size: 15px; font-weight: 500; transition: background 0.2s; }
            .btn:hover { background: var(--lobios-purple-light); }
            .btn:disabled { background: #bdc3c7; cursor: not-allowed; }
            .result { margin-top: 15px; padding: 10px; background: #e6e6fa; border-radius: 6px; display: none; color: var(--lobios-dark); }
            .error { background: #f8d7da; color: #721c24; }
            .loading { display: none; text-align: center; margin-top: 10px; }
            input[type="number"] { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
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
            <img src="/static/logo.png" alt="Lobios">
            <nav>
                <a href="#" class="active">Dashboard</a>
                <a href="#">Serviços</a>
                <a href="#">Relatórios</a>
                <a href="#">API</a>
            </nav>
        </div>
        <div class="main">
            <div class="topbar">
                <div class="user">Lobios</div>
            </div>
            <div class="container">
                <div class="header">
                    <h1>PDF Platform</h1>
                    <p>Manipule seus arquivos PDF facilmente</p>
                </div>
                <div class="tools-grid">
                    <!-- Converter para Word -->
                    <div class="tool-card">
                        <h3>📄 PDF para Word</h3>
                        <input type="file" id="pdfToWord" accept=".pdf" class="file-input">
                        <button onclick="convertToWord()" class="btn">Converter para DOCX</button>
                        <div class="loading" id="loadingWord">Convertendo...</div>
                        <div class="result" id="resultWord"></div>
                    </div>
                    <!-- Converter para Excel -->
                    <div class="tool-card">
                        <h3>📊 PDF para Excel</h3>
                        <input type="file" id="pdfToExcel" accept=".pdf" class="file-input">
                        <button onclick="convertToExcel()" class="btn">Converter para XLSX</button>
                        <div class="loading" id="loadingExcel">Convertendo...</div>
                        <div class="result" id="resultExcel"></div>
                    </div>
                    <!-- Juntar PDFs -->
                    <div class="tool-card">
                        <h3>🔗 Juntar PDFs</h3>
                        <input type="file" id="mergePdfs" accept=".pdf" multiple class="file-input">
                        <button onclick="mergePdfs()" class="btn">Juntar Arquivos</button>
                        <div class="loading" id="loadingMerge">Juntando...</div>
                        <div class="result" id="resultMerge"></div>
                    </div>
                    <!-- Separar PDF -->
                    <div class="tool-card">
                        <h3>✂️ Separar PDF</h3>
                        <input type="file" id="splitPdf" accept=".pdf" class="file-input">
                        <input type="number" placeholder="Página inicial" id="startPage" min="1">
                        <input type="number" placeholder="Página final" id="endPage" min="1">
                        <button onclick="splitPdf()" class="btn">Extrair Páginas</button>
                        <div class="loading" id="loadingSplit">Extraindo...</div>
                        <div class="result" id="resultSplit"></div>
                    </div>
                    <!-- Comprimir PDF -->
                    <div class="tool-card">
                        <h3>🗜️ Comprimir PDF</h3>
                        <input type="file" id="compressPdf" accept=".pdf" class="file-input">
                        <button onclick="compressPdf()" class="btn">Comprimir Arquivo</button>
                        <div class="loading" id="loadingCompress">Comprimindo...</div>
                        <div class="result" id="resultCompress"></div>
                    </div>
                    <!-- Comparar PDFs -->
                    <div class="tool-card">
                        <h3>🔍 Comparar PDFs</h3>
                        <input type="file" id="comparePdf1" accept=".pdf" class="file-input" placeholder="PDF 1">
                        <input type="file" id="comparePdf2" accept=".pdf" class="file-input" placeholder="PDF 2">
                        <button onclick="comparePdfs()" class="btn">Comparar Arquivos</button>
                        <div class="loading" id="loadingCompare">Comparando...</div>
                        <div class="result" id="resultCompare"></div>
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
        </script>
    </body>
    </html>
    """

@app.post("/convert/word")
async def convert_to_word(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    # Salvar arquivo temporário
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extrair texto do PDF
        with open(temp_path, 'rb') as pdf_file:
            reader = pypdf.PdfReader(pdf_file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        
        # Criar documento Word
        doc = Document()
        doc.add_paragraph(text)
        
        # Salvar e retornar
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_converted.docx"
        doc.save(output_path)
        
        return FileResponse(output_path, filename=file.filename.replace('.pdf', '.docx'))
    
    finally:
        # Limpar arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/convert/excel")
async def convert_to_excel(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Extrair texto do PDF
        with open(temp_path, 'rb') as pdf_file:
            reader = pypdf.PdfReader(pdf_file)
            
        # Criar planilha Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "PDF Content"
        
        row = 1
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()
            ws.cell(row=row, column=1, value=f"Página {page_num}")
            ws.cell(row=row, column=2, value=text)
            row += 1
        
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_converted.xlsx"
        wb.save(output_path)
        
        return FileResponse(output_path, filename=file.filename.replace('.pdf', '.xlsx'))
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/merge")
async def merge_pdfs(files: List[UploadFile] = File(...)):
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="Necessário pelo menos 2 arquivos")
    
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
        
        # Juntar PDFs
        merger = pypdf.PdfWriter()
        for path in temp_paths:
            merger.append(path)
        
        output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_merged.pdf"
        with open(output_path, 'wb') as output_file:
            merger.write(output_file)
        
        return FileResponse(output_path, filename="merged.pdf")
    
    finally:
        # Limpar arquivos temporários
        for path in temp_paths:
            if os.path.exists(path):
                os.remove(path)

@app.post("/split")
async def split_pdf(file: UploadFile = File(...), start_page: int = Form(...), end_page: int = Form(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        with open(temp_path, 'rb') as pdf_file:
            reader = pypdf.PdfReader(pdf_file)
            
            if start_page < 1 or end_page > len(reader.pages) or start_page > end_page:
                raise HTTPException(status_code=400, detail="Páginas inválidas")
            
            writer = pypdf.PdfWriter()
            for i in range(start_page - 1, end_page):
                writer.add_page(reader.pages[i])
            
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_extracted.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return FileResponse(output_path, filename="extracted_pages.pdf")
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/compress")
async def compress_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Arquivo deve ser PDF")
    
    temp_path = f"{UPLOAD_DIR}/{uuid.uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        with open(temp_path, 'rb') as pdf_file:
            reader = pypdf.PdfReader(pdf_file)
            writer = pypdf.PdfWriter()
            
            for page in reader.pages:
                writer.add_page(page)
            
            # Compressão básica
            writer.compress_identical_objects()
            
            output_path = f"{OUTPUT_DIR}/{uuid.uuid4()}_compressed.pdf"
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return FileResponse(output_path, filename=file.filename.replace('.pdf', '_compressed.pdf'))
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/compare")
async def compare_pdfs(file1: UploadFile = File(...), file2: UploadFile = File(...)):
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)