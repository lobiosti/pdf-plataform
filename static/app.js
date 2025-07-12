// Funções globais para PDF Platform

function mergePdfs() {
    const files = document.getElementById('mergePdfs').files;
    if (files.length < 2) return alert('Selecione pelo menos 2 arquivos PDF');
    showLoading('Merge');
    const formData = new FormData();
    for (let file of files) formData.append('files', file);
    fetch('/merge', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                showResult('Merge', `<a href="${url}" download="merged.pdf">📥 Download PDF Combinado</a>`);
            } else {
                throw new Error('Erro ao juntar arquivos');
            }
        })
        .catch(() => showResult('Merge', 'Erro ao juntar arquivos', true))
        .finally(() => hideLoading('Merge'));
}

function splitPdf() {
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
    fetch('/split', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                showResult('Split', `<a href="${url}" download="extracted_pages.pdf">📥 Download Páginas Extraídas</a>`);
            } else {
                throw new Error('Erro ao extrair páginas');
            }
        })
        .catch(() => showResult('Split', 'Erro ao extrair páginas', true))
        .finally(() => hideLoading('Split'));
}

function convertToWord() {
    const file = document.getElementById('pdfToWord').files[0];
    if (!file) return alert('Selecione um arquivo PDF');
    showLoading('Word');
    const formData = new FormData();
    formData.append('file', file);
    fetch('/convert/word', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                showResult('Word', `<a href="${url}" download="${file.name.replace('.pdf', '.docx')}">📥 Download DOCX</a>`);
            } else {
                throw new Error('Erro na conversão');
            }
        })
        .catch(() => showResult('Word', 'Erro ao converter arquivo', true))
        .finally(() => hideLoading('Word'));
}

function convertToExcel() {
    const file = document.getElementById('pdfToExcel').files[0];
    if (!file) return alert('Selecione um arquivo PDF');
    showLoading('Excel');
    const formData = new FormData();
    formData.append('file', file);
    fetch('/convert/excel', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                showResult('Excel', `<a href="${url}" download="${file.name.replace('.pdf', '.xlsx')}">📥 Download XLSX</a>`);
            } else {
                throw new Error('Erro na conversão');
            }
        })
        .catch(() => showResult('Excel', 'Erro ao converter arquivo', true))
        .finally(() => hideLoading('Excel'));
}

function compressPdf() {
    const file = document.getElementById('compressPdf').files[0];
    if (!file) return alert('Selecione um arquivo PDF');
    showLoading('Compress');
    const formData = new FormData();
    formData.append('file', file);
    fetch('/compress', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                showResult('Compress', `<a href="${url}" download="${file.name.replace('.pdf', '_compressed.pdf')}">📥 Download PDF Comprimido</a>`);
            } else {
                throw new Error('Erro ao comprimir');
            }
        })
        .catch(() => showResult('Compress', 'Erro ao comprimir arquivo', true))
        .finally(() => hideLoading('Compress'));
}

function comparePdfs() {
    const file1 = document.getElementById('comparePdf1').files[0];
    const file2 = document.getElementById('comparePdf2').files[0];
    if (!file1 || !file2) return alert('Selecione os dois arquivos PDF');
    showLoading('Compare');
    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);
    fetch('/compare', { method: 'POST', body: formData })
        .then(async response => {
            const result = await response.json();
            if (response.ok) {
                showResult('Compare', result.message);
            } else {
                throw new Error(result.detail);
            }
        })
        .catch(() => showResult('Compare', 'Erro ao comparar arquivos', true))
        .finally(() => hideLoading('Compare'));
}

function removePages() {
    const file = document.getElementById('removePagesPdf').files[0];
    const pages = document.getElementById('removePagesList').value;
    if (!file || !pages) return alert('Selecione o PDF e informe as páginas a remover');
    document.getElementById('loadingRemovePages').style.display = 'block';
    document.getElementById('resultRemovePages').style.display = 'none';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('pages', pages);
    fetch('/remove-pages', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                document.getElementById('resultRemovePages').innerHTML = `<a href="${url}" download="removed_pages.pdf">📥 Download PDF sem páginas</a>`;
                document.getElementById('resultRemovePages').className = 'result';
            } else {
                throw new Error('Erro ao remover páginas');
            }
        })
        .catch(() => {
            document.getElementById('resultRemovePages').innerHTML = 'Erro ao remover páginas';
            document.getElementById('resultRemovePages').className = 'result error';
        })
        .finally(() => {
            document.getElementById('loadingRemovePages').style.display = 'none';
            document.getElementById('resultRemovePages').style.display = 'block';
        });
}

function extractPages() {
    const file = document.getElementById('extractPagesPdf').files[0];
    const pages = document.getElementById('extractPagesList').value;
    if (!file || !pages) return alert('Selecione o PDF e informe as páginas a extrair');
    document.getElementById('loadingExtractPages').style.display = 'block';
    document.getElementById('resultExtractPages').style.display = 'none';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('pages', pages);
    fetch('/extract-pages', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                document.getElementById('resultExtractPages').innerHTML = `<a href="${url}" download="extracted_pages.pdf">📥 Download Páginas Extraídas</a>`;
                document.getElementById('resultExtractPages').className = 'result';
            } else {
                throw new Error('Erro ao extrair páginas');
            }
        })
        .catch(() => {
            document.getElementById('resultExtractPages').innerHTML = 'Erro ao extrair páginas';
            document.getElementById('resultExtractPages').className = 'result error';
        })
        .finally(() => {
            document.getElementById('loadingExtractPages').style.display = 'none';
            document.getElementById('resultExtractPages').style.display = 'block';
        });
}

function organizePdfPages() {
    const file = document.getElementById('organizePdf').files[0];
    const order = document.getElementById('organizeOrder').value;
    if (!file || !order) return alert('Selecione o PDF e informe a nova ordem das páginas');
    document.getElementById('loadingOrganizePdf').style.display = 'block';
    document.getElementById('resultOrganizePdf').style.display = 'none';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('order', order);
    fetch('/organize-pages', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                document.getElementById('resultOrganizePdf').innerHTML = `<a href="${url}" download="organized.pdf">📥 Download PDF Organizado</a>`;
                document.getElementById('resultOrganizePdf').className = 'result';
            } else {
                throw new Error('Erro ao organizar páginas');
            }
        })
        .catch(() => {
            document.getElementById('resultOrganizePdf').innerHTML = 'Erro ao organizar páginas';
            document.getElementById('resultOrganizePdf').className = 'result error';
        })
        .finally(() => {
            document.getElementById('loadingOrganizePdf').style.display = 'none';
            document.getElementById('resultOrganizePdf').style.display = 'block';
        });
}

function insertPageNumbers() {
    const file = document.getElementById('numberPdf').files[0];
    if (!file) return alert('Selecione um PDF');
    document.getElementById('loadingNumberPdf').style.display = 'block';
    document.getElementById('resultNumberPdf').style.display = 'none';
    const formData = new FormData();
    formData.append('file', file);
    fetch('/edit/add-page-numbers', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                document.getElementById('resultNumberPdf').innerHTML = `<a href="${url}" download="numbered.pdf">📥 Download PDF Numerado</a>`;
                document.getElementById('resultNumberPdf').className = 'result';
            } else {
                throw new Error('Erro ao inserir números');
            }
        })
        .catch(() => {
            document.getElementById('resultNumberPdf').innerHTML = 'Erro ao inserir números';
            document.getElementById('resultNumberPdf').className = 'result error';
        })
        .finally(() => {
            document.getElementById('loadingNumberPdf').style.display = 'none';
            document.getElementById('resultNumberPdf').style.display = 'block';
        });
}

function insertWatermark() {
    const file = document.getElementById('watermarkPdf').files[0];
    const text = document.getElementById('watermarkText').value;
    if (!file || !text) return alert('Selecione o PDF e informe o texto da marca d\'água');
    document.getElementById('loadingWatermarkPdf').style.display = 'block';
    document.getElementById('resultWatermarkPdf').style.display = 'none';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('text', text);
    fetch('/edit/add-watermark', { method: 'POST', body: formData })
        .then(async response => {
            if (response.ok) {
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                document.getElementById('resultWatermarkPdf').innerHTML = `<a href="${url}" download="watermarked.pdf">📥 Download PDF com Marca d'Água</a>`;
                document.getElementById('resultWatermarkPdf').className = 'result';
            } else {
                throw new Error('Erro ao inserir marca d\'água');
            }
        })
        .catch(() => {
            document.getElementById('resultWatermarkPdf').innerHTML = 'Erro ao inserir marca d\'água';
            document.getElementById('resultWatermarkPdf').className = 'result error';
        })
        .finally(() => {
            document.getElementById('loadingWatermarkPdf').style.display = 'none';
            document.getElementById('resultWatermarkPdf').style.display = 'block';
        });
}

// Alternância de categorias na barra lateral
window.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.category-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            document.querySelectorAll('.category-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            document.querySelectorAll('.tools-grid').forEach(grid => grid.style.display = 'none');
            const cat = this.getAttribute('data-category');
            document.getElementById(cat).style.display = 'grid';
            document.getElementById('category-title').textContent = this.textContent;
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
});

// Modal Política de Privacidade
window.addEventListener('DOMContentLoaded', function() {
    var privacyBtn = document.getElementById('privacyBtn');
    var privacyModal = document.getElementById('privacyModal');
    var closePrivacy = document.getElementById('closePrivacy');
    if (privacyBtn && privacyModal && closePrivacy) {
        privacyBtn.onclick = function() {
            privacyModal.style.display = 'flex';
        };
        closePrivacy.onclick = function() {
            privacyModal.style.display = 'none';
        };
        window.addEventListener('click', function(event) {
            if (event.target === privacyModal) {
                privacyModal.style.display = 'none';
            }
        });
    }
});

// Utilitários globais
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