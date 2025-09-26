/**
 * Dialfa Business Intelligence Dashboard
 * Main JavaScript functionality
 */

// Global configuration
const CONFIG = {
    API_BASE_URL: '',
    REFRESH_INTERVAL: 300000, // 5 minutes
    CHART_COLORS: {
        primary: '#033663',
        success: '#28a745',
        warning: '#ffc107',
        danger: '#dc3545',
        info: '#17a2b8'
    }
};

// Global state
let refreshIntervals = [];
let chartInstances = {};

/**
 * Initialize dashboard functionality
 */
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    startAutoRefresh();
});

/**
 * Initialize dashboard components
 */
function initializeDashboard() {
    console.log('Initializing Dialfa BI Dashboard...');
    
    // Add fade-in animation to cards
    document.querySelectorAll('.card').forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Handle window resize for responsive charts
    window.addEventListener('resize', debounce(handleWindowResize, 250));
    
    // Handle navigation clicks
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', handleNavigation);
    });
    
    // Handle chart interactions
    document.addEventListener('click', handleChartInteractions);
}

/**
 * Start auto-refresh functionality
 */
function startAutoRefresh() {
    // Refresh dashboard data every 5 minutes
    const dashboardRefresh = setInterval(() => {
        console.log('Auto-refreshing dashboard data...');
        if (typeof loadDashboardData === 'function') {
            loadDashboardData();
        }
        if (typeof loadAlerts === 'function') {
            loadAlerts();
        }
    }, CONFIG.REFRESH_INTERVAL);
    
    refreshIntervals.push(dashboardRefresh);
}

/**
 * Handle window resize events
 */
function handleWindowResize() {
    // Resize all Plotly charts
    Object.keys(chartInstances).forEach(chartId => {
        if (document.getElementById(chartId)) {
            Plotly.Plots.resize(chartId);
        }
    });
}

/**
 * Handle navigation clicks
 */
function handleNavigation(event) {
    const link = event.target.closest('.nav-link');
    if (link && !link.classList.contains('dropdown-toggle')) {
        // Add loading state
        const originalText = link.innerHTML;
        link.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...';
        
        // Restore original text after a short delay
        setTimeout(() => {
            link.innerHTML = originalText;
        }, 1000);
    }
}

/**
 * Handle chart interactions
 */
function handleChartInteractions(event) {
    // Handle button group clicks for chart filters
    if (event.target.matches('.btn-group .btn')) {
        const buttonGroup = event.target.closest('.btn-group');
        if (buttonGroup) {
            // Update active state
            buttonGroup.querySelectorAll('.btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
        }
    }
}

/**
 * Utility Functions
 */

/**
 * Format currency values
 */
function formatCurrency(amount, options = {}) {
    if (amount == null || isNaN(amount)) return '$0';
    
    const {
        showCents = false,
        compact = true
    } = options;
    
    if (compact) {
        if (Math.abs(amount) >= 1000000) {
            return '$' + (amount / 1000000).toFixed(1) + 'M';
        } else if (Math.abs(amount) >= 1000) {
            return '$' + (amount / 1000).toFixed(1) + 'K';
        }
    }
    
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: showCents ? 2 : 0,
        maximumFractionDigits: showCents ? 2 : 0
    }).format(amount);
}

/**
 * Format percentage values
 */
function formatPercentage(value, decimals = 1) {
    if (value == null || isNaN(value)) return '0%';
    return value.toFixed(decimals) + '%';
}

/**
 * Format numbers with separators
 */
function formatNumber(value, decimals = 0) {
    if (value == null || isNaN(value)) return '0';
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

/**
 * Show loading state for an element
 */
function showLoading(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="loading">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">${message}</span>
                </div>
                <div class="ms-2">${message}</div>
            </div>
        `;
    }
}

/**
 * Show error state for an element
 */
function showError(elementId, message, showRetry = false) {
    const element = document.getElementById(elementId);
    if (element) {
        let html = `
            <div class="alert alert-danger d-flex align-items-center" role="alert">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <div>${message}</div>
            </div>
        `;
        
        if (showRetry) {
            html += `
                <div class="text-center mt-3">
                    <button class="btn btn-outline-primary btn-sm" onclick="location.reload()">
                        <i class="bi bi-arrow-clockwise me-1"></i>
                        Retry
                    </button>
                </div>
            `;
        }
        
        element.innerHTML = html;
    }
}

/**
 * Show success message
 */
function showSuccess(message, duration = 5000) {
    const alertHtml = `
        <div class="alert alert-success alert-dismissible fade show" role="alert">
            <i class="bi bi-check-circle me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Insert at the top of the main content
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alertHtml);
        
        // Auto-dismiss after duration
        setTimeout(() => {
            const alert = container.querySelector('.alert-success');
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }
}

/**
 * Debounce function to limit function calls
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle function to limit function calls
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Make API request with error handling
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(CONFIG.API_BASE_URL + url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'error') {
            throw new Error(data.error || 'API request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * Chart creation utilities
 */
const ChartUtils = {
    /**
     * Get default Plotly layout
     */
    getDefaultLayout(title = '', options = {}) {
        return {
            title: title,
            font: {
                family: 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
                size: 12
            },
            plot_bgcolor: 'rgba(0,0,0,0)',
            paper_bgcolor: 'rgba(0,0,0,0)',
            margin: { t: 40, r: 40, b: 60, l: 80 },
            showlegend: false,
            ...options
        };
    },
    
    /**
     * Get default Plotly config
     */
    getDefaultConfig() {
        return {
            responsive: true,
            displayModeBar: false,
            displaylogo: false
        };
    },
    
    /**
     * Create a line chart
     */
    createLineChart(elementId, data, options = {}) {
        const trace = {
            x: data.x,
            y: data.y,
            type: 'scatter',
            mode: 'lines+markers',
            name: options.name || 'Data',
            line: {
                color: options.color || CONFIG.CHART_COLORS.primary,
                width: 3
            },
            marker: {
                size: 8,
                color: options.color || CONFIG.CHART_COLORS.primary
            }
        };
        
        const layout = this.getDefaultLayout(options.title, {
            xaxis: { title: options.xTitle || '' },
            yaxis: { title: options.yTitle || '' }
        });
        
        Plotly.newPlot(elementId, [trace], layout, this.getDefaultConfig());
        chartInstances[elementId] = true;
    },
    
    /**
     * Create a bar chart
     */
    createBarChart(elementId, data, options = {}) {
        const trace = {
            x: data.x,
            y: data.y,
            type: 'bar',
            name: options.name || 'Data',
            marker: {
                color: options.color || CONFIG.CHART_COLORS.primary
            }
        };
        
        const layout = this.getDefaultLayout(options.title, {
            xaxis: { title: options.xTitle || '' },
            yaxis: { title: options.yTitle || '' }
        });
        
        Plotly.newPlot(elementId, [trace], layout, this.getDefaultConfig());
        chartInstances[elementId] = true;
    },
    
    /**
     * Create a pie chart
     */
    createPieChart(elementId, data, options = {}) {
        const trace = {
            labels: data.labels,
            values: data.values,
            type: 'pie',
            textinfo: 'label+percent',
            textposition: 'outside',
            marker: {
                colors: options.colors || [
                    CONFIG.CHART_COLORS.primary,
                    CONFIG.CHART_COLORS.success,
                    CONFIG.CHART_COLORS.warning,
                    CONFIG.CHART_COLORS.danger,
                    CONFIG.CHART_COLORS.info
                ]
            }
        };
        
        const layout = this.getDefaultLayout(options.title, {
            margin: { t: 40, r: 40, b: 40, l: 40 }
        });
        
        Plotly.newPlot(elementId, [trace], layout, this.getDefaultConfig());
        chartInstances[elementId] = true;
    }
};

/**
 * Export utilities for global access
 */
window.DialfaBI = {
    formatCurrency,
    formatPercentage,
    formatNumber,
    showLoading,
    showError,
    showSuccess,
    apiRequest,
    ChartUtils,
    CONFIG
};

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', function() {
    // Clear all intervals
    refreshIntervals.forEach(interval => clearInterval(interval));
    refreshIntervals = [];
    
    // Clear chart instances
    chartInstances = {};
});
