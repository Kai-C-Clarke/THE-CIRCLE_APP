// Server status check
async function checkServerStatus() {
    try {
        const response = await fetch('/api/test');
        const data = await response.json();
        document.getElementById('serverStatus').textContent = 'Connected ✓';
        document.getElementById('serverStatus').style.color = '#10b981';
        return true;
    } catch (error) {
        document.getElementById('serverStatus').textContent = 'Disconnected ✗';
        document.getElementById('serverStatus').style.color = '#ef4444';
        console.error('Server connection failed:', error);
        return false;
    }
}

// DOM Elements
let currentFile = null;
let selectedFiles = [];

// Initialize drag and drop
function initDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, unhighlight, false);
    });
    
    uploadArea.addEventListener('drop', handleDrop, false);
    
    function highlight() {
        uploadArea.classList.add('drag-over');
    }
    
    function unhighlight() {
        uploadArea.classList.remove('drag-over');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    // File input change
    const fileInput = document.getElementById('fileInput');
    fileInput.addEventListener('change', function(e) {
        handleFiles(this.files);
    });
}

// Handle selected files
function handleFiles(files) {
    selectedFiles = Array.from(files);
    
    if (selectedFiles.length > 0) {
        currentFile = selectedFiles[0];
        showUploadForm();
    }
}

// Show upload form
function showUploadForm() {
    if (!currentFile) return;
    
    document.getElementById('uploadArea').style.display = 'none';
    document.getElementById('uploadForm').style.display = 'block';
    
    // Auto-fill title with filename (without extension)
    const titleInput = document.getElementById('title');
    const fileName = currentFile.name;
    const nameWithoutExt = fileName.lastIndexOf('.') > 0 
        ? fileName.substring(0, fileName.lastIndexOf('.')) 
        : fileName;
    
    titleInput.value = nameWithoutExt;
    document.getElementById('uploaded_by').value = 'Catherine';
}

// Cancel upload
function cancelUpload() {
    document.getElementById('uploadForm').style.display = 'none';
    document.getElementById('uploadArea').style.display = 'block';
    document.getElementById('uploadProgress').style.display = 'none';
    
    // Reset form
    document.getElementById('fileInput').value = '';
    document.getElementById('description').value = '';
    document.getElementById('tags').value = '';
    
    currentFile = null;
    selectedFiles = [];
}

// Upload file
async function uploadFile() {
    if (!currentFile) {
        alert('Please select a file first');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', currentFile);
    formData.append('title', document.getElementById('title').value);
    formData.append('description', document.getElementById('description').value);
    formData.append('uploaded_by', document.getElementById('uploaded_by').value);
    formData.append('tags', document.getElementById('tags').value);
    formData.append('family_group_id', 1);
    
    // Show progress
    document.getElementById('uploadForm').style.display = 'none';
    document.getElementById('uploadProgress').style.display = 'block';
    
    try {
        const response = await fetch('/api/media/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            document.getElementById('progressFill').style.width = '100%';
            document.getElementById('progressText').textContent = 'Upload complete!';
            
            // Reset after delay
            setTimeout(() => {
                cancelUpload();
                loadMedia(); // Refresh media grid
            }, 1500);
        } else {
            throw new Error(result.message || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        document.getElementById('progressText').textContent = `Error: ${error.message}`;
        document.getElementById('progressText').style.color = '#ef4444';
        
        setTimeout(() => {
            cancelUpload();
        }, 3000);
    }
}

// Load media from server
async function loadMedia() {
    const mediaGrid = document.getElementById('mediaGrid');
    mediaGrid.innerHTML = `
        <div class="loading">
            <i class="fas fa-spinner fa-spin fa-2x"></i>
            <p>Loading memories...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/media');
        const result = await response.json();
        
        if (result.status === 'success') {
            displayMedia(result.media);
        } else {
            throw new Error(result.message || 'Failed to load media');
        }
    } catch (error) {
        console.error('Error loading media:', error);
        mediaGrid.innerHTML = `
            <div class="loading">
                <i class="fas fa-exclamation-triangle fa-2x" style="color: #ef4444;"></i>
                <p>Failed to load memories. Please try again.</p>
            </div>
        `;
    }
}

// Display media in grid
function displayMedia(mediaItems) {
    const mediaGrid = document.getElementById('mediaGrid');
    const filterType = document.getElementById('filterType').value;
    
    if (mediaItems.length === 0) {
        mediaGrid.innerHTML = `
            <div class="loading">
                <i class="fas fa-images fa-2x" style="color: #adb5bd;"></i>
                <p>No memories yet. Upload the first one!</p>
            </div>
        `;
        return;
    }
    
    // Filter media
    let filteredMedia = mediaItems;
    if (filterType !== 'all') {
        filteredMedia = mediaItems.filter(item => {
            if (filterType === 'image') {
                return ['png', 'jpg', 'jpeg', 'gif'].includes(item.filetype);
            } else if (filterType === 'video') {
                return ['mp4', 'mov', 'avi', 'mkv'].includes(item.filetype);
            } else if (filterType === 'document') {
                return ['pdf', 'doc', 'docx'].includes(item.filetype);
            }
            return true;
        });
    }
    
    mediaGrid.innerHTML = filteredMedia.map(item => `
        <div class="media-item" onclick="viewMedia(${item.id}, '${item.filetype}')">
            <div class="media-thumbnail">
                ${getThumbnailHTML(item)}
            </div>
            <div class="media-info">
                <h3 title="${item.title}">${item.title}</h3>
                <div class="media-meta">
                    <i class="fas fa-user"></i> ${item.uploaded_by}
                    <br>
                    <i class="far fa-calendar"></i> ${new Date(item.upload_date).toLocaleDateString()}
                </div>
                ${item.tags ? `<div class="media-tags">${item.tags.split(',').map(tag => `<span>#${tag.trim()}</span>`).join(' ')}</div>` : ''}
                <button class="delete-btn" onclick="deleteMedia(${item.id}, event)">
                    <i class="fas fa-trash"></i> Delete
                </button>
            </div>
        </div>
    `).join('');
}

// Get thumbnail HTML based on file type
function getThumbnailHTML(item) {
    const fileType = item.filetype.toLowerCase();
    
    if (['png', 'jpg', 'jpeg', 'gif'].includes(fileType)) {
        if (item.thumbnail) {
            return `<img src="/static/thumbnails/${item.thumbnail}" alt="${item.title}">`;
        }
        return `<img src="/static/uploads/${item.filename}" alt="${item.title}">`;
    }
    
    if (['mp4', 'mov', 'avi', 'mkv'].includes(fileType)) {
        return `<i class="fas fa-video" style="color: #667eea;"></i>`;
    }
    
    if (['pdf'].includes(fileType)) {
        return `<i class="fas fa-file-pdf" style="color: #ef4444;"></i>`;
    }
    
    if (['doc', 'docx'].includes(fileType)) {
        return `<i class="fas fa-file-word" style="color: #2563eb;"></i>`;
    }
    
    return `<i class="fas fa-file" style="color: #adb5bd;"></i>`;
}

// View media in modal
function viewMedia(mediaId, fileType) {
    fetch(`/api/media/${mediaId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const media = data.media;
                let content = '';
                
                if (['png', 'jpg', 'jpeg', 'gif'].includes(fileType)) {
                    content = `
                        <img src="/static/uploads/${media.filename}" alt="${media.title}" style="max-width: 100%; border-radius: 10px;">
                    `;
                } else if (['mp4', 'mov', 'avi', 'mkv'].includes(fileType)) {
                    content = `
                        <video controls style="max-width: 100%; border-radius: 10px;">
                            <source src="/static/uploads/${media.filename}" type="video/${fileType}">
                            Your browser does not support the video tag.
                        </video>
                    `;
                } else {
                    content = `
                        <div style="text-align: center; padding: 40px;">
                            <i class="fas fa-file-${fileType === 'pdf' ? 'pdf' : 'word'} fa-5x" 
                               style="color: ${fileType === 'pdf' ? '#ef4444' : '#2563eb'}; margin-bottom: 20px;"></i>
                            <h3>${media.title}</h3>
                            <p>${media.description || 'No description'}</p>
                            <a href="/static/uploads/${media.filename}" download class="browse-btn" style="margin-top: 20px;">
                                <i class="fas fa-download"></i> Download File
                            </a>
                        </div>
                    `;
                }
                
                document.getElementById('modalBody').innerHTML = `
                    ${content}
                    <div style="margin-top: 20px;">
                        <h3>${media.title}</h3>
                        <p>${media.description || 'No description'}</p>
                        <p><strong>Uploaded by:</strong> ${media.uploaded_by}</p>
                        <p><strong>Date:</strong> ${new Date(media.upload_date).toLocaleString()}</p>
                        ${media.tags ? `<p><strong>Tags:</strong> ${media.tags}</p>` : ''}
                    </div>
                `;
                
                document.getElementById('mediaModal').style.display = 'flex';
            }
        })
        .catch(error => {
            console.error('Error loading media:', error);
            alert('Failed to load media details');
        });
}

// Close modal
function closeModal() {
    document.getElementById('mediaModal').style.display = 'none';
}

// Delete media
async function deleteMedia(mediaId, event) {
    event.stopPropagation(); // Prevent triggering viewMedia
    
    if (!confirm('Are you sure you want to delete this memory?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/media/${mediaId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // Remove from grid
            loadMedia();
        } else {
            throw new Error(result.message || 'Delete failed');
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert(`Delete failed: ${error.message}`);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Check server connection
    checkServerStatus();
    
    // Initialize drag and drop
    initDragAndDrop();
    
    // Load initial media
    loadMedia();
    
    // Set up filter change listener
    document.getElementById('filterType').addEventListener('change', loadMedia);
    
    // Close modal on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
    
    // Close modal on background click
    document.getElementById('mediaModal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
});