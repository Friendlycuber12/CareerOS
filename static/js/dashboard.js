/**
 * Dashboard Specific JavaScript
 * Handles dashboard interactions, kanban drag-and-drop
 */

document.addEventListener('DOMContentLoaded', () => {
    // Kanban Drag and Drop Logic
    const kanbanCards = document.querySelectorAll('.kanban-card');
    const kanbanColumns = document.querySelectorAll('.kanban-column');
    
    let draggedCard = null;

    kanbanCards.forEach(card => {
        card.setAttribute('draggable', true);
        
        card.addEventListener('dragstart', () => {
            draggedCard = card;
            setTimeout(() => {
                card.style.opacity = '0.5';
            }, 0);
        });

        card.addEventListener('dragend', () => {
            setTimeout(() => {
                draggedCard.style.opacity = '1';
                draggedCard = null;
            }, 0);
        });
    });

    kanbanColumns.forEach(column => {
        column.addEventListener('dragover', e => {
            e.preventDefault();
            const afterElement = getDragAfterElement(column, e.clientY);
            if (draggedCard) {
                if (afterElement == null) {
                    column.appendChild(draggedCard);
                } else {
                    column.insertBefore(draggedCard, afterElement);
                }
            }
        });
        
        column.addEventListener('drop', e => {
            e.preventDefault();
            // Could add API call here to update status
            // window.showToast('Application status updated');
        });
    });

    function getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.kanban-card:not([style*="opacity: 0.5"])')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    // Set active nav item based on current URL
    const navItems = document.querySelectorAll('.nav-item');
    const currentPath = window.location.pathname;
    
    navItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        } else if (currentPath === '/' && item.getAttribute('href') === '/dashboard') {
            // Default mapping for root to dashboard if needed
        }
    });
});
