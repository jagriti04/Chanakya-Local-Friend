// This file can be used to add client-side interactivity to the memory management page.
// For example, you could add a confirmation dialog before deleting a memory.

document.addEventListener('DOMContentLoaded', function() {
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (!confirm('Are you sure you want to delete this memory?')) {
                event.preventDefault();
            }
        });
    });
});
