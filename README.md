# PDF Platform Lobios

Ferramentas online para facilitar o manuseio de arquivos PDF com segurança e praticidade.

## Funcionalidades
- **Organizar PDF**: Juntar, dividir, remover páginas, extrair páginas, organizar ordem.
- **Converter em PDF**: JPG, Word, Excel, PowerPoint, HTML para PDF.
- **Converter de PDF**: PDF para Word, Excel, etc.
- **Editar PDF**: Inserir números de página, inserir marca d'água.
- **Segurança**: Proteger PDF com senha, desbloquear PDF, comparar arquivos.

## Tecnologias
- [FastAPI](https://fastapi.tiangolo.com/)
- [pypdf](https://pypdf.readthedocs.io/)
- [fpdf](https://pyfpdf.github.io/fpdf2/)
- [Pillow](https://python-pillow.org/)
- [python-docx](https://python-docx.readthedocs.io/)
- [openpyxl](https://openpyxl.readthedocs.io/)
- [PyPDF2](https://pypdf2.readthedocs.io/)
- [reportlab](https://www.reportlab.com/)
- [pandas](https://pandas.pydata.org/)
- [python-pptx](https://python-pptx.readthedocs.io/)
- [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/)

## Instalação local
1. Clone o repositório:
   ```bash
   git clone https://github.com/SEU_USUARIO/NOME_DO_REPO.git
   cd NOME_DO_REPO
   ```
2. Crie e ative o ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute a aplicação:
   ```bash
   python main.py
   ```
5. Acesse em [http://localhost:8000](http://localhost:8000)

## Deploy no Railway
1. Faça push do código para o GitHub.
2. No Railway, crie um novo projeto e conecte ao seu repositório.
3. Configure o comando de start:
   ```bash
   python main.py
   ```
4. O Railway instala automaticamente as dependências do `requirements.txt`.
5. Acesse o endereço gerado pelo Railway para usar online.

## Dependências principais
Inclua no seu `requirements.txt`:
```
fastapi
uvicorn
python-multipart
pypdf
python-docx
openpyxl
fpdf
pandas
python-pptx
reportlab
beautifulsoup4
Pillow
PyPDF2
```

## Política de Privacidade
- Todos os arquivos enviados são processados de forma segura e excluídos automaticamente após a conversão.
- Não armazenamos, visualizamos ou compartilhamos seus documentos.
- Utilizamos apenas cookies essenciais para o funcionamento da plataforma.

---

Desenvolvido por [Lobios](https://lobios.io/) — Segurança, Tecnologia e Inovação. 