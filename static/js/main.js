/**
 * Main JavaScript file for Smart Parking System
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Format currency inputs (in INR)
    const currencyInputs = document.querySelectorAll('.currency-input');
    currencyInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^\d.]/g, '');
            if (value) {
                // Format as INR with 2 decimal places
                value = parseFloat(value).toFixed(2);
                e.target.value = value;
                
                // Add a data attribute with the equivalent USD value for backend processing
                const usdValue = (parseFloat(value) / 75).toFixed(2);
                e.target.dataset.usdValue = usdValue;
            }
        });
    });
    
    // Format date inputs
    const dateInputs = document.querySelectorAll('.date-input');
    dateInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 8) value = value.slice(0, 8);
            
            if (value.length > 4) {
                value = value.slice(0, 4) + '-' + value.slice(4);
            }
            if (value.length > 7) {
                value = value.slice(0, 7) + '-' + value.slice(7);
            }
            
            e.target.value = value;
        });
    });
    
    // Format credit card inputs
    const ccInputs = document.querySelectorAll('.cc-input');
    ccInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 16) value = value.slice(0, 16);
            
            // Add spaces every 4 digits
            let formattedValue = '';
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 4 === 0) formattedValue += ' ';
                formattedValue += value[i];
            }
            
            e.target.value = formattedValue;
        });
    });
    
    // Format expiry date inputs
    const expiryInputs = document.querySelectorAll('.expiry-input');
    expiryInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 4) value = value.slice(0, 4);
            
            if (value.length > 2) {
                value = value.slice(0, 2) + '/' + value.slice(2);
            }
            
            e.target.value = value;
        });
    });
    
    // Format CVV inputs
    const cvvInputs = document.querySelectorAll('.cvv-input');
    cvvInputs.forEach(function(input) {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length > 4) value = value.slice(0, 4);
            e.target.value = value;
        });
    });
    
    // Handle form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        }, false);
    });
    
    // Fetch space status for real-time updates
    function updateSpaceStatus() {
        const statusContainer = document.getElementById('space-status-container');
        if (statusContainer) {
            fetch('/spaces')
                .then(response => response.json())
                .then(data => {
                    // Update UI with space status
                    let availableCount = 0;
                    let totalCount = Object.keys(data).length;
                    
                    for (const key in data) {
                        if (data[key].is_available) {
                            availableCount++;
                        }
                        
                        // Update individual space elements if they exist
                        const spaceElement = document.getElementById(`space-${data[key].id}`);
                        if (spaceElement) {
                            if (data[key].is_available) {
                                spaceElement.classList.add('available');
                                spaceElement.classList.remove('occupied', 'booked');
                            } else if (data[key].is_booked) {
                                spaceElement.classList.add('booked');
                                spaceElement.classList.remove('available', 'occupied');
                            } else {
                                spaceElement.classList.add('occupied');
                                spaceElement.classList.remove('available', 'booked');
                            }
                        }
                    }
                    
                    // Update availability counter if it exists
                    const availabilityCounter = document.getElementById('availability-counter');
                    if (availabilityCounter) {
                        availabilityCounter.textContent = `${availableCount} / ${totalCount}`;
                    }
                })
                .catch(error => console.error('Error fetching space data:', error));
        }
    }
    
    // Update space status every 10 seconds if the container exists
    if (document.getElementById('space-status-container')) {
        updateSpaceStatus();
        setInterval(updateSpaceStatus, 10000);
    }
});

/**
 * Calculate the price based on hourly rate and duration
 * @param {number} hourlyRate - The hourly rate
 * @param {number} duration - The duration in hours
 * @returns {number} - The total price
 */
function calculatePrice(hourlyRate, duration) {
    return hourlyRate * duration;
}

/**
 * Format a number as currency in Indian Rupees (INR)
 * @param {number} value - The value to format in USD
 * @returns {string} - The formatted currency string in INR
 */
function formatCurrency(value) {
    // Convert USD to INR (approximate exchange rate: 1 USD = 75 INR)
    const inrValue = parseFloat(value) * 75;
    return '₹' + inrValue.toFixed(2);
}

/**
 * Animate counting up to a value
 * @param {string} elementId - The ID of the element to animate
 * @param {number} start - The starting value
 * @param {number} end - The ending value
 * @param {number} duration - The duration of the animation in milliseconds
 */
function animateValue(elementId, start, end, duration) {
    const obj = document.getElementById(elementId);
    if (!obj) return;
    
    const range = end - start;
    const minTimer = 50;
    let stepTime = Math.abs(Math.floor(duration / range));
    stepTime = Math.max(stepTime, minTimer);
    
    let startTime = new Date().getTime();
    let endTime = startTime + duration;
    let timer;
    
    function run() {
        let now = new Date().getTime();
        let remaining = Math.max((endTime - now) / duration, 0);
        let value = Math.round(end - (remaining * range));
        obj.innerHTML = value;
        if (value == end) {
            clearInterval(timer);
        }
    }
    
    timer = setInterval(run, stepTime);
    run();
}

/**
 * Export a table to CSV
 * @param {string} tableId - The ID of the table to export
 * @param {string} filename - The filename for the CSV
 */
function exportTableToCSV(tableId, filename) {
    const csv = [];
    const rows = document.querySelectorAll(`#${tableId} tr`);
    
    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            // Replace any commas in the cell text to avoid CSV issues
            let text = cols[j].innerText.replace(/,/g, ' ');
            // Wrap in quotes if there are spaces
            if (text.includes(' ')) {
                text = `"${text}"`;
            }
            row.push(text);
        }
        
        csv.push(row.join(','));
    }
    
    // Download CSV file
    downloadCSV(csv.join('\n'), filename);
}

/**
 * Download a CSV file
 * @param {string} csv - The CSV content
 * @param {string} filename - The filename for the CSV
 */
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: 'text/csv'});
    const downloadLink = document.createElement('a');
    
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}