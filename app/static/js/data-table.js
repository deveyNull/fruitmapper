class DataTableManager {
    constructor(rawData, initialFilters = {}) {
        this.rawData = rawData;
        this.filterCriteria = initialFilters;
        this.columns = rawData.length > 0 ? Object.keys(rawData[0]) : [];
        this.visibleColumns = new Set(this.columns);
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Column visibility toggle
        const toggle = document.getElementById('column-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                document.getElementById('column-dropdown').classList.toggle('hidden');
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            const dropdown = document.getElementById('column-dropdown');
            const toggle = document.getElementById('column-toggle');
            if (dropdown && !dropdown.contains(e.target) && !toggle.contains(e.target)) {
                dropdown.classList.add('hidden');
            }
        });

        // Apply filter button
        const applyButton = document.getElementById('apply-filter');
        if (applyButton) {
            applyButton.addEventListener('click', () => this.applyFilters());
        }
    }

    setupFilterInputs() {
        const container = document.getElementById('filter-inputs');
        if (!container) return;

        container.innerHTML = this.columns.map(column => `
            <div class="filter-input">
                <label class="block text-sm font-medium text-gray-700 mb-1">${column}</label>
                <input type="text" 
                       data-column="${column}"
                       value="${this.filterCriteria[column] || ''}"
                       class="shadow-sm w-full rounded-md border-gray-300 focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50">
            </div>
        `).join('');
    }

    setupColumnManager() {
        const checkboxContainer = document.getElementById('column-checkboxes');
        if (!checkboxContainer) return;

        // Add deselect button and checkboxes container
        checkboxContainer.innerHTML = `
            <div class="flex justify-end mb-3">
                <button id="deselect-all" 
                        class="text-sm text-red-600 hover:text-red-800">
                    Deselect All
                </button>
            </div>
            <div class="space-y-2">
                ${this.columns.map(column => `
                    <label class="flex items-center">
                        <input type="checkbox" 
                               data-column="${column}"
                               class="form-checkbox h-4 w-4 text-blue-600"
                               ${this.visibleColumns.has(column) ? 'checked' : ''}>
                        <span class="ml-2 text-gray-700">${column}</span>
                    </label>
                `).join('')}
            </div>
        `;

        // Handle deselect all
        document.getElementById('deselect-all').addEventListener('click', () => {
            this.visibleColumns.clear();
            checkboxContainer.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = false;
            });
            this.displayData(this.rawData);
        });

        // Handle individual checkbox changes
        checkboxContainer.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox') {
                const column = e.target.dataset.column;
                if (e.target.checked) {
                    this.visibleColumns.add(column);
                } else {
                    this.visibleColumns.delete(column);
                }
                this.displayData(this.rawData);
            }
        });
    }

    applyFilters() {
        const inputs = document.querySelectorAll('#filter-inputs input');
        this.filterCriteria = {};
        
        inputs.forEach(input => {
            if (input.value.trim()) {
                this.filterCriteria[input.dataset.column] = input.value.trim();
            }
        });

        const filteredData = this.rawData.filter(row => {
            return Object.entries(this.filterCriteria).every(([column, value]) => {
                const cellValue = String(row[column] || '').toLowerCase();
                return cellValue.includes(String(value).toLowerCase());
            });
        });

        this.displayData(filteredData);
    }

    displayData(data, previewMode = false) {
        const container = document.getElementById('data-table');
        if (!container || !data.length) {
            container.innerHTML = '<p class="text-center text-gray-500 py-4">No data to display</p>';
            return;
        }

        const visibleCols = Array.from(this.visibleColumns);
        const displayData = previewMode ? data.slice(0, 5) : data;

        container.innerHTML = `
            ${previewMode ? '<div class="text-sm text-gray-500 mb-2">Showing first 5 rows of ' + data.length + ' total rows</div>' : ''}
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        ${visibleCols.map(column => `
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                ${column}
                            </th>
                        `).join('')}
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    ${displayData.map(row => `
                        <tr>
                            ${visibleCols.map(column => `
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                    ${row[column] !== null ? row[column] : ''}
                                </td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    getCurrentState() {
        return {
            rawData: this.rawData,
            filterCriteria: this.filterCriteria,
            visibleColumns: Array.from(this.visibleColumns)
        };
    }
    exportVisibleData(data) {
        const visibleCols = Array.from(this.visibleColumns);
        
        // Filter the data to only include visible columns
        const exportData = data.map(row => {
            const exportRow = {};
            visibleCols.forEach(col => {
                exportRow[col] = row[col];
            });
            return exportRow;
        });
    
        // Convert to CSV
        const csv = Papa.unparse(exportData);
        
        // Create download link
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.setAttribute('download', 'exported_data.csv');
        link.style.display = 'none';
        document.body.appendChild(link);
        
        // Trigger download
        link.click();
        
        // Cleanup
        document.body.removeChild(link);
    }
}

// Export the class if using modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DataTableManager;
}

