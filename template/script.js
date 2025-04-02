document.addEventListener('DOMContentLoaded', () => {

    // --- Theme Toggle ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const themeToggleIcon = document.getElementById('theme-toggle-icon');
    const docElement = document.documentElement;

    const setTheme = (isDark) => {
        if (isDark) {
            docElement.classList.add('is-dark-mode');
            themeToggleIcon.classList.remove('fa-sun');
            themeToggleIcon.classList.add('fa-moon');
            localStorage.setItem('theme', 'dark');
        } else {
            docElement.classList.remove('is-dark-mode');
            themeToggleIcon.classList.remove('fa-moon');
            themeToggleIcon.classList.add('fa-sun');
            localStorage.setItem('theme', 'light');
        }
    };

    const currentTheme = localStorage.getItem('theme') || 'dark'; // Default dark
    setTheme(currentTheme === 'dark');

    themeToggleBtn.addEventListener('click', () => {
        setTheme(!docElement.classList.contains('is-dark-mode'));
    });

    // --- Form Elements & State ---
    const analysisForm = document.getElementById('analysisForm');
    const urlInput = document.getElementById('url');
    const modelChoiceSelect = document.getElementById('modelChoice');
    const useBothCheckbox = document.getElementById('useBoth');
    const submitButton = document.getElementById('submitButton');
    const buttonText = document.getElementById('buttonText');
    const buttonLoader = document.getElementById('buttonLoader');
    const errorDiv = document.getElementById('error');
    const errorMessageSpan = document.getElementById('errorMessage');
    const resultDiv = document.getElementById('result');
    const loadingOverlay = document.getElementById('loadingOverlay');

    // File Input Elements
    const resumeInput = document.getElementById('resumeFile');
    const portfolioInput = document.getElementById('portfolioFile');
    const resumeDropZone = document.getElementById('resumeDropZone');
    const portfolioDropZone = document.getElementById('portfolioDropZone');
    const resumeFileInfo = document.getElementById('resumeFileInfo');
    const portfolioFileInfo = document.getElementById('portfolioFileInfo');
    const resumeFileNameSpan = document.getElementById('resumeFileName');
    const portfolioFileNameSpan = document.getElementById('portfolioFileName');
    const removeResumeBtn = document.getElementById('removeResume');
    const removePortfolioBtn = document.getElementById('removePortfolio');

    // --- File Input Handling (Drag & Drop + Click) ---
    const setupFileInput = (nativeInput, dropZone, fileInfo, fileNameSpan, removeBtn) => {
        const placeholder = dropZone.querySelector('.file-placeholder');

        const showFileInfo = (file) => {
            fileNameSpan.textContent = file.name;
            placeholder.style.display = 'none';
            fileInfo.style.display = 'flex';
            dropZone.classList.add('has-file');
        };

        const hideFileInfo = () => {
            nativeInput.value = ''; // Clear native input
            fileNameSpan.textContent = '';
            placeholder.style.display = 'block';
            fileInfo.style.display = 'none';
            dropZone.classList.remove('has-file');
        };

        // Handle file selection via click
        nativeInput.addEventListener('change', () => {
            if (nativeInput.files.length > 0) {
                showFileInfo(nativeInput.files[0]);
            } else {
                hideFileInfo(); // Handles case where user cancels selection
            }
        });

        // Handle remove button click
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent triggering drop zone click
            hideFileInfo();
        });

        // Drag and Drop listeners
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.add('is-dragover'), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => dropZone.classList.remove('is-dragover'), false);
        });

        dropZone.addEventListener('drop', (e) => {
            const dt = e.dataTransfer;
            if (dt.files.length > 0) {
                // Assign dropped file(s) to the native input
                nativeInput.files = dt.files;
                // Manually trigger change event to update display
                nativeInput.dispatchEvent(new Event('change'));
            }
        }, false);

        // Allow clicking the drop zone to trigger the native input
        dropZone.addEventListener('click', () => {
            if (!dropZone.classList.contains('has-file')) { // Only trigger if no file selected
                 nativeInput.click();
            }
        });
    };

    setupFileInput(resumeInput, resumeDropZone, resumeFileInfo, resumeFileNameSpan, removeResumeBtn);
    setupFileInput(portfolioInput, portfolioDropZone, portfolioFileInfo, portfolioFileNameSpan, removePortfolioBtn);


    // --- Form Submission ---
    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Clear previous state
        errorDiv.classList.remove('is-active');
        resultDiv.classList.remove('is-active');
        resultDiv.innerHTML = ''; // Clear previous results immediately

        // Show loading state
        submitButton.classList.add('is-loading');
        submitButton.disabled = true;
        loadingOverlay.classList.add('is-active'); // Show overlay

        const formData = new FormData();
        formData.append('url', urlInput.value);
        if (resumeInput.files[0]) formData.append('resume_file', resumeInput.files[0]);
        if (portfolioInput.files[0]) formData.append('portfolio_file', portfolioInput.files[0]);
        formData.append('use_both', useBothCheckbox.checked ? 'true' : 'false');
        formData.append('model_choice', modelChoiceSelect.value);

        try {
            const response = await axios.post('http://127.0.0.1:8000/analyze/', formData, {
                // timeout: 90000 // Longer timeout might be needed
            });

            // Inject and animate results
            resultDiv.innerHTML = processResultHtml(response.data); // Process HTML before injecting
            // Delay slightly before adding class to ensure transition works
            setTimeout(() => {
                 resultDiv.style.display = 'block'; // Make sure it's visible before animating
                 resultDiv.classList.add('is-active');
                 resultDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);


        } catch (err) {
            const message = err.response?.data?.detail || err.message || 'An unexpected error occurred.';
            errorMessageSpan.textContent = message;
            errorDiv.classList.add('is-active');
             errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
            console.error("Analysis Error:", err.response || err);
        } finally {
            // Hide loading state
            submitButton.classList.remove('is-loading');
            submitButton.disabled = false;
            loadingOverlay.classList.remove('is-active');
        }
    });

    // Dismiss error notification
    errorDiv.querySelector('.close-button').addEventListener('click', () => {
        errorDiv.classList.remove('is-active');
    });

    // --- Helper to Process Result HTML ---
    // Adds icons and classes to the HTML coming from the backend
    function processResultHtml(htmlString) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(htmlString, 'text/html');
        const resultWrapper = doc.querySelector('.analysis-result'); // Target the main div from format.py

        if (resultWrapper) {
            // Add suitability class to H2
            const h2 = resultWrapper.querySelector('h2');
            if (h2 && h2.textContent.toLowerCase().includes('suitability: yes')) {
                h2.classList.add('suitability-yes');
            } else if (h2 && h2.textContent.toLowerCase().includes('suitability: no')) {
                 h2.classList.add('suitability-no');
            }

            // Add icons to H3 sections
             resultWrapper.querySelectorAll('h3').forEach(h3 => {
                const text = h3.textContent.toLowerCase();
                if (text.includes('job details')) h3.classList.add('icon-job');
                else if (text.includes('matched skills')) h3.classList.add('icon-skills');
                else if (text.includes('interview questions')) h3.classList.add('icon-questions');
                else if (text.includes('reasons for unsuitability')) h3.classList.add('icon-reasons');
                else if (text.includes('suggestions for improvement')) h3.classList.add('icon-suggestions');
             });

             // Add class to Q&A lists if needed
             resultWrapper.querySelectorAll('h4').forEach(h4 => {
                 if(h4.textContent.toLowerCase().includes('technical questions') || h4.textContent.toLowerCase().includes('behavioral questions')) {
                     const nextUl = h4.nextElementSibling;
                     if(nextUl && nextUl.tagName === 'UL') {
                         nextUl.classList.add('qa-list');
                     }
                 }
             });

            return resultWrapper.outerHTML; // Return the modified HTML
        }
        return htmlString; // Return original if structure not found
    }

});
