document.getElementById('uploadForm').addEventListener('submit', function (e) {
    e.preventDefault();
    const formData = new FormData();
    formData.append('semester', document.getElementById('semester').value);
    formData.append('subject', document.getElementById('subject').value);
    formData.append('topic', document.getElementById('topic').value);
    formData.append('file', document.getElementById('file').files[0]);

    fetch('/upload_note', {
        method: 'POST',
        body: formData
    }).then(response => response.json())
      .then(data => alert(data.message));
});