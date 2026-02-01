/**
 * Task management app with intentional accessibility issues:
 * - No keyboard event handlers
 * - No ARIA live regions
 * - No focus management
 */

let tasks = [
    { id: 1, title: 'Buy groceries', completed: false },
    { id: 2, title: 'Call mom', completed: true },
    { id: 3, title: 'Finish project', completed: false }
];

let nextId = 4;

// ISSUE: Only handles click, not keyboard (Enter/Space)
function addTask() {
    const input = document.querySelector('.add-task input');
    const title = input.value.trim();

    if (!title) {
        // ISSUE: No accessible error message
        alert('Please enter a task');
        return;
    }

    tasks.push({
        id: nextId++,
        title: title,
        completed: false
    });

    input.value = '';
    renderTasks();

    // ISSUE: No announcement to screen readers that task was added
}

// ISSUE: No keyboard support (should be triggered by Enter/Space)
function toggleTask(id) {
    const task = tasks.find(t => t.id === id);
    if (task) {
        task.completed = !task.completed;
        renderTasks();
        // ISSUE: No announcement of state change
    }
}

// ISSUE: No confirmation, no keyboard support
function deleteTask(id) {
    tasks = tasks.filter(t => t.id !== id);
    renderTasks();
    // ISSUE: No announcement that task was deleted
    // ISSUE: No focus management after deletion
}

function renderTasks() {
    const list = document.querySelector('.task-list');
    const status = document.querySelector('.status');

    // ISSUE: Using innerHTML to rebuild - loses focus state
    // Clear and rebuild using DOM methods
    list.textContent = '';
    
    tasks.forEach(task => {
        const div = document.createElement('div');
        div.className = 'task-item' + (task.completed ? ' completed' : '');
        div.setAttribute('onclick', 'toggleTask(' + task.id + ')');
        
        const img = document.createElement('img');
        img.src = task.completed ? 'checkbox-checked.png' : 'checkbox.png';
        
        const span = document.createElement('span');
        span.textContent = task.title;
        if (task.completed) {
            span.style.textDecoration = 'line-through';
        }
        
        const deleteBtn = document.createElement('div');
        deleteBtn.className = 'delete';
        deleteBtn.setAttribute('onclick', 'event.stopPropagation(); deleteTask(' + task.id + ')');
        deleteBtn.textContent = '×';
        
        div.appendChild(img);
        div.appendChild(span);
        div.appendChild(deleteBtn);
        list.appendChild(div);
    });

    const completed = tasks.filter(t => t.completed).length;
    status.textContent = tasks.length + ' tasks, ' + completed + ' completed';

    // ISSUE: Status update not announced to screen readers
}

// ISSUE: No keyboard event listeners for Enter key on input
document.addEventListener('DOMContentLoaded', function() {
    // Just render, no keyboard support added
    renderTasks();
});
