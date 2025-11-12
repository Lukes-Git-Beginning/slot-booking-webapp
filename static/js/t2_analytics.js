/**
 * T2 Analytics Dashboard - JavaScript Logic
 * Handles draw history, filtering, pagination, and charts
 */

const T2Analytics = (function() {
  'use strict';

  // State
  let currentPage = 0;
  let itemsPerPage = 20;
  let totalDraws = 0;
  let currentFilters = {
    search: '',
    closer: 'all',
    startDate: null,
    endDate: null
  };

  let drawStats = null;
  let combinedStats = null;

  // Initialize
  function init(stats, combined) {
    drawStats = stats;
    combinedStats = combined;

    loadDrawHistory();
    initializeCharts();
    setupEventListeners();
  }

  // Load Draw History with Pagination and Filters
  function loadDrawHistory(page = 0) {
    currentPage = page;
    const offset = page * itemsPerPage;

    // Build query params
    const params = new URLSearchParams({
      limit: itemsPerPage,
      offset: offset
    });

    if (currentFilters.closer !== 'all') {
      params.append('closer', currentFilters.closer);
    }

    if (currentFilters.startDate) {
      params.append('start_date', currentFilters.startDate);
    }

    if (currentFilters.endDate) {
      params.append('end_date', currentFilters.endDate);
    }

    // Show loading
    const tbody = document.getElementById('draw-history-body');
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center py-8">
          <div class="flex items-center justify-center gap-3">
            <span class="loading loading-spinner loading-md text-primary"></span>
            <span class="text-base-content/60">Lade Historie...</span>
          </div>
        </td>
      </tr>
    `;

    // Fetch data
    fetch(`/t2/api/my-draw-history?${params.toString()}`)
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          totalDraws = data.total_count;
          renderDrawHistory(data.draws);
          renderPagination(data);
        } else {
          showError('Fehler beim Laden der Historie');
        }
      })
      .catch(error => {
        console.error('Error loading draw history:', error);
        showError('Netzwerkfehler beim Laden');
      });
  }

  // Search Draws
  function searchDraws(query) {
    if (!query || query.length < 2) {
      loadDrawHistory(0);
      return;
    }

    const tbody = document.getElementById('draw-history-body');
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center py-8">
          <div class="flex items-center justify-center gap-3">
            <span class="loading loading-spinner loading-md text-primary"></span>
            <span class="text-base-content/60">Suche...</span>
          </div>
        </td>
      </tr>
    `;

    fetch(`/t2/api/search-draws?q=${encodeURIComponent(query)}`)
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          renderDrawHistory(data.results);
          document.getElementById('pagination-info').textContent = `${data.count} Ergebnisse`;
          document.getElementById('pagination-controls').innerHTML = '';
        } else {
          showError('Fehler bei der Suche');
        }
      })
      .catch(error => {
        console.error('Error searching draws:', error);
        showError('Netzwerkfehler bei der Suche');
      });
  }

  // Render Draw History Table
  function renderDrawHistory(draws) {
    const tbody = document.getElementById('draw-history-body');

    if (!draws || draws.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center py-8 text-base-content/60">
            <i data-lucide="inbox" class="w-12 h-12 mx-auto mb-3 opacity-50"></i>
            <p>Keine Würfe gefunden</p>
          </td>
        </tr>
      `;
      lucide.createIcons();
      return;
    }

    tbody.innerHTML = draws.map(draw => `
      <tr class="hover:bg-base-200/50 transition-colors">
        <td class="font-medium">${draw.formatted_date || 'N/A'}</td>
        <td class="text-base-content/70">${draw.formatted_time || 'N/A'}</td>
        <td>
          <div class="font-semibold text-primary">${draw.customer_name || 'Unbekannt'}</div>
        </td>
        <td>
          <div class="badge badge-lg ${getCloserBadgeColor(draw.closer)}">
            ${draw.closer || 'N/A'}
          </div>
        </td>
        <td class="text-base-content/70">
          ${draw.bucket_size_after || 'N/A'}/20
        </td>
        <td>
          <span class="badge ${draw.draw_type === 'T2' ? 'badge-info' : 'badge-success'}">
            ${draw.draw_type || 'N/A'}
          </span>
        </td>
      </tr>
    `).join('');

    lucide.createIcons();
  }

  // Get Closer Badge Color
  function getCloserBadgeColor(closer) {
    const colors = {
      'Alex': 'badge-info',
      'David': 'badge-secondary',
      'Jose': 'badge-accent'
    };
    return colors[closer] || 'badge-ghost';
  }

  // Render Pagination
  function renderPagination(data) {
    const totalPages = Math.ceil(data.total_count / itemsPerPage);
    const start = data.offset + 1;
    const end = Math.min(data.offset + data.returned_count, data.total_count);

    // Update info text
    document.getElementById('pagination-info').textContent = `${start}-${end} von ${data.total_count}`;

    // Render pagination buttons
    const controls = document.getElementById('pagination-controls');

    if (totalPages <= 1) {
      controls.innerHTML = '';
      return;
    }

    let html = '';

    // Previous button
    html += `
      <button class="join-item btn btn-sm ${currentPage === 0 ? 'btn-disabled' : ''}"
              onclick="T2Analytics.goToPage(${currentPage - 1})"
              ${currentPage === 0 ? 'disabled' : ''}>
        «
      </button>
    `;

    // Page buttons (show max 5 pages)
    const maxVisible = 5;
    let startPage = Math.max(0, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible);

    if (endPage - startPage < maxVisible) {
      startPage = Math.max(0, endPage - maxVisible);
    }

    for (let i = startPage; i < endPage; i++) {
      html += `
        <button class="join-item btn btn-sm ${i === currentPage ? 'btn-active btn-primary' : ''}"
                onclick="T2Analytics.goToPage(${i})">
          ${i + 1}
        </button>
      `;
    }

    // Next button
    html += `
      <button class="join-item btn btn-sm ${currentPage >= totalPages - 1 ? 'btn-disabled' : ''}"
              onclick="T2Analytics.goToPage(${currentPage + 1})"
              ${currentPage >= totalPages - 1 ? 'disabled' : ''}>
        »
      </button>
    `;

    controls.innerHTML = html;
  }

  // Go to Page
  function goToPage(page) {
    if (page < 0) return;
    loadDrawHistory(page);
  }

  // Initialize Charts
  function initializeCharts() {
    if (typeof ApexCharts === 'undefined') {
      console.warn('ApexCharts not loaded, charts will not be displayed');
      return;
    }

    initializeCloserDistributionChart();
    initializeTimelineChart();
  }

  // Closer Distribution Pie Chart
  function initializeCloserDistributionChart() {
    if (!drawStats || !drawStats.closer_distribution) return;

    const distribution = drawStats.closer_distribution;
    const closers = Object.keys(distribution);
    const counts = Object.values(distribution);

    if (closers.length === 0) {
      document.getElementById('chart-closer-distribution').innerHTML = '<p class="text-center text-base-content/60 py-20">Noch keine Daten</p>';
      return;
    }

    const options = {
      series: counts,
      chart: {
        type: 'donut',
        height: 320,
        background: 'transparent',
        fontFamily: 'Inter, sans-serif'
      },
      labels: closers,
      colors: ['#2196F3', '#9C27B0', '#795548'],
      theme: {
        mode: 'dark'
      },
      legend: {
        position: 'bottom',
        labels: {
          colors: '#a0aec0'
        }
      },
      dataLabels: {
        enabled: true,
        style: {
          fontSize: '14px',
          fontWeight: 'bold'
        }
      },
      plotOptions: {
        pie: {
          donut: {
            size: '60%',
            labels: {
              show: true,
              total: {
                show: true,
                label: 'Gesamt',
                fontSize: '18px',
                fontWeight: 'bold',
                color: '#d4af6a'
              }
            }
          }
        }
      },
      tooltip: {
        theme: 'dark',
        y: {
          formatter: function(value) {
            return value + ' Würfe';
          }
        }
      }
    };

    const chart = new ApexCharts(document.querySelector("#chart-closer-distribution"), options);
    chart.render();
  }

  // Draw Timeline Line Chart
  function initializeTimelineChart() {
    fetch('/t2/api/draw-timeline?days=30')
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          renderTimelineChart(data.dates, data.counts);
        }
      })
      .catch(error => {
        console.error('Error loading timeline data:', error);
      });
  }

  function renderTimelineChart(dates, counts) {
    if (!dates || dates.length === 0) {
      document.getElementById('chart-draw-timeline').innerHTML = '<p class="text-center text-base-content/60 py-20">Noch keine Daten</p>';
      return;
    }

    // Format dates for display
    const formattedDates = dates.map(date => {
      const d = new Date(date);
      return `${d.getDate()}.${d.getMonth() + 1}`;
    });

    const options = {
      series: [{
        name: 'Würfe',
        data: counts
      }],
      chart: {
        type: 'area',
        height: 320,
        background: 'transparent',
        fontFamily: 'Inter, sans-serif',
        toolbar: {
          show: false
        },
        zoom: {
          enabled: false
        }
      },
      dataLabels: {
        enabled: false
      },
      stroke: {
        curve: 'smooth',
        width: 3,
        colors: ['#d4af6a']
      },
      fill: {
        type: 'gradient',
        gradient: {
          shadeIntensity: 1,
          opacityFrom: 0.5,
          opacityTo: 0.1,
          stops: [0, 100]
        },
        colors: ['#d4af6a']
      },
      xaxis: {
        categories: formattedDates,
        labels: {
          style: {
            colors: '#a0aec0'
          }
        }
      },
      yaxis: {
        title: {
          text: 'Anzahl Würfe',
          style: {
            color: '#a0aec0'
          }
        },
        labels: {
          style: {
            colors: '#a0aec0'
          }
        }
      },
      theme: {
        mode: 'dark'
      },
      grid: {
        borderColor: '#374151',
        strokeDashArray: 4
      },
      tooltip: {
        theme: 'dark',
        x: {
          show: true
        },
        y: {
          formatter: function(value) {
            return value + ' Würfe';
          }
        }
      }
    };

    const chart = new ApexCharts(document.querySelector("#chart-draw-timeline"), options);
    chart.render();
  }

  // Setup Event Listeners
  function setupEventListeners() {
    // Expose filter functions to Alpine.js/global scope
    window.filterDraws = function() {
      loadDrawHistory(0);
    };

    window.handleDateRange = function(event) {
      const value = event.target.value;
      const now = new Date();

      switch(value) {
        case 'week':
          currentFilters.startDate = new Date(now.setDate(now.getDate() - 7)).toISOString();
          break;
        case 'month':
          currentFilters.startDate = new Date(now.setMonth(now.getMonth() - 1)).toISOString();
          break;
        case '90days':
          currentFilters.startDate = new Date(now.setDate(now.getDate() - 90)).toISOString();
          break;
        default:
          currentFilters.startDate = null;
          currentFilters.endDate = null;
      }

      loadDrawHistory(0);
    };
  }

  // Show Error
  function showError(message) {
    const tbody = document.getElementById('draw-history-body');
    tbody.innerHTML = `
      <tr>
        <td colspan="6" class="text-center py-8 text-error">
          <i data-lucide="alert-circle" class="w-12 h-12 mx-auto mb-3"></i>
          <p>${message}</p>
        </td>
      </tr>
    `;
    lucide.createIcons();
  }

  // Public API
  return {
    init: init,
    goToPage: goToPage,
    searchDraws: searchDraws
  };
})();

// Make T2Analytics globally available
window.T2Analytics = T2Analytics;
