document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const submitBtn = document.getElementById('submit-btn');
    const uploadProgress = document.getElementById('upload-progress');
    const progressBar = document.getElementById('progress-bar');
    const filenameDisplay = document.getElementById('filename');
    const statusText = document.getElementById('status-text');
    const uploadCard = document.querySelector('.upload-card');
    const resultCard = document.getElementById('result-card');
    const resetBtn = document.getElementById('reset-btn');
    const extractedDataList = document.getElementById('extracted-data-list');

    let selectedFile = null;

    // Click to open file dialog
    dropZone.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    function handleFile(file) {
        if (file.type !== 'application/pdf') {
            alert('Por favor, selecione apenas arquivos PDF.');
            return;
        }
        selectedFile = file;
        
        // Update UI
        dropZone.classList.add('hidden');
        uploadProgress.classList.remove('hidden');
        filenameDisplay.textContent = file.name;
        statusText.textContent = 'Pronto para enviar';
        progressBar.style.width = '100%';
        progressBar.style.animation = 'none'; // Stop indeterminate animation
        
        submitBtn.disabled = false;
    }

    submitBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        // UI changes for processing state
        submitBtn.disabled = true;
        statusText.textContent = 'Processando documento...';
        progressBar.style.animation = 'progressIndeterminate 2s infinite linear';

        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch('/api/process-document', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Erro ao processar documento');
            }

            // Success
            showResults(result.extracted);
        } catch (error) {
            alert(`Erro: ${error.message}`);
            // Reset UI slightly
            statusText.textContent = 'Falha no processamento';
            submitBtn.disabled = false;
            progressBar.style.animation = 'none';
        }
    });

    function showResults(data) {
        uploadCard.classList.add('hidden');
        resultCard.classList.remove('hidden');
        
        extractedDataList.innerHTML = '';
        
        const labels = {
            'Processo_Judicial': 'Processo Judicial',
            'Processo_judicial': 'Processo Judicial',
            'Data_Judicial': 'Data Judicial',
            'Num_SEI': 'Número SEI',
            'Objeto': 'Objeto (Dataset)',
            'Setor': 'Setor (Dataset)',
            'Reu': 'Réu (Dataset)',
            'Atribuido': 'Atribuído',
            'Observacoes': 'Observações',
            'Autuacao_CDJ': 'Autuação na CDJ'
        };

        for (const [key, value] of Object.entries(data)) {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="label">${labels[key] || key}</span>
                <span class="value">${value || '-'}</span>
            `;
            extractedDataList.appendChild(li);
        }
    }

    resetBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        
        // Reset UI
        resultCard.classList.add('hidden');
        uploadCard.classList.remove('hidden');
        dropZone.classList.remove('hidden');
        uploadProgress.classList.add('hidden');
        submitBtn.disabled = true;
    });
});
