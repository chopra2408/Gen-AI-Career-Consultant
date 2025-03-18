document.addEventListener('DOMContentLoaded', function() {
    // Initialize Materialize select element
    var elems = document.querySelectorAll('select');
    M.FormSelect.init(elems);
});

document.getElementById('analysisForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const url = document.getElementById('url').value;
    const resumeFile = document.getElementById('resumeFile').files[0];
    const portfolioFile = document.getElementById('portfolioFile').files[0];
    const useBoth = document.getElementById('useBoth').checked;
    const modelChoice = document.getElementById('modelChoice').value; // Get the selected model

    const formData = new FormData();
    formData.append('url', url);
    if (resumeFile) formData.append('resume_file', resumeFile);
    if (portfolioFile) formData.append('portfolio_file', portfolioFile);
    formData.append('use_both', useBoth);
    formData.append('model_choice', modelChoice);

    // Show spinner
    document.getElementById('spinner').style.display = 'block';
    document.getElementById('error').textContent = '';
    document.getElementById('result').innerHTML = '';

    try {
        const response = await axios.post('http://127.0.0.1:8000/analyze/', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        // Use innerHTML so that the HTML response is rendered
        document.getElementById('result').innerHTML = response.data;
    } catch (err) {
        document.getElementById('error').textContent = err.response?.data?.detail || 'An error occurred. Please try again.';
    } finally {
        // Hide spinner
        document.getElementById('spinner').style.display = 'none';
    }
});

// File removal functionality for Resume
document.getElementById('resumeFile').addEventListener('change', function() {
    const removeBtn = document.getElementById('removeResume');
    if (this.files.length > 0) {
        removeBtn.style.display = 'inline';
    }
});

document.getElementById('removeResume').addEventListener('click', function() {
    const resumeInput = document.getElementById('resumeFile');
    resumeInput.value = '';
    this.style.display = 'none';
    // Clear the associated file-path input
    resumeInput.closest('.file-field').querySelector('.file-path.validate').value = '';
});

// File removal functionality for Portfolio
document.getElementById('portfolioFile').addEventListener('change', function() {
    const removeBtn = document.getElementById('removePortfolio');
    if (this.files.length > 0) {
        removeBtn.style.display = 'inline';
    }
});

document.getElementById('removePortfolio').addEventListener('click', function() {
    const portfolioInput = document.getElementById('portfolioFile');
    portfolioInput.value = '';
    this.style.display = 'none';
    // Clear the associated file-path input (assumes second instance)
    portfolioInput.closest('.file-field').querySelector('.file-path.validate').value = '';
});
