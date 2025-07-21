"""
Data Quality Dashboard for HVLC_DB

This module provides a simple web-based dashboard for data quality monitoring
using Flask and Plotly.
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import plotly.express as px
import plotly.graph_objects as go
from flask import Flask, render_template, request, jsonify, send_from_directory

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_quality_monitor import DataQualityMonitor
from utils.config import get_config
from utils.logger import get_logger

# Configure logging
logger = get_logger()
config = get_config()

# Initialize Flask app
app = Flask(__name__)

# Initialize monitor
monitor = None

# Create dashboard directory
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
os.makedirs(dashboard_dir, exist_ok=True)

# Create templates directory
templates_dir = os.path.join(dashboard_dir, "templates")
os.makedirs(templates_dir, exist_ok=True)

# Create static directory
static_dir = os.path.join(dashboard_dir, "static")
os.makedirs(static_dir, exist_ok=True)

# Create HTML template
with open(os.path.join(templates_dir, "index.html"), "w") as f:
    f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Data Quality Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <style>
        .card {
            margin-bottom: 20px;
        }
        .violation-high {
            background-color: #f8d7da;
        }
        .violation-medium {
            background-color: #fff3cd;
        }
        .violation-low {
            background-color: #d1e7dd;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <h1 class="mt-4">Data Quality Dashboard</h1>
        <p>Last updated: <span id="last-updated"></span></p>
        
        <div class="row">
            <div class="col-md-3">
                <div class="card">
                    <div class="card-header">Tables</div>
                    <div class="card-body">
                        <div class="list-group" id="table-list">
                            <!-- Tables will be populated here -->
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-header">Actions</div>
                    <div class="card-body">
                        <button class="btn btn-primary" onclick="runCheck()">Run Quality Check</button>
                        <button class="btn btn-secondary mt-2" onclick="generateReport()">Generate Report</button>
                    </div>
                </div>
            </div>
            
            <div class="col-md-9">
                <div class="card">
                    <div class="card-header">Summary</div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <div class="card text-white bg-primary">
                                    <div class="card-body">
                                        <h5 class="card-title">Tables Checked</h5>
                                        <p class="card-text" id="tables-checked">0</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card text-white bg-warning">
                                    <div class="card-body">
                                        <h5 class="card-title">Tables with Issues</h5>
                                        <p class="card-text" id="tables-with-issues">0</p>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="card text-white bg-danger">
                                    <div class="card-body">
                                        <h5 class="card-title">Total Violations</h5>
                                        <p class="card-text" id="total-violations">0</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mt-4" id="violations-chart"></div>
                    </div>
                </div>
                
                <div class="card" id="table-details-card" style="display: none;">
                    <div class="card-header">Table Details: <span id="table-name"></span></div>
                    <div class="card-body">
                        <ul class="nav nav-tabs" id="table-tabs">
                            <li class="nav-item">
                                <a class="nav-link active" data-bs-toggle="tab" href="#violations-tab">Violations</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" data-bs-toggle="tab" href="#statistics-tab">Statistics</a>
                            </li>
                            <li class="nav-item">
                                <a class="nav-link" data-bs-toggle="tab" href="#trends-tab">Trends</a>
                            </li>
                        </ul>
                        
                        <div class="tab-content mt-3">
                            <div class="tab-pane fade show active" id="violations-tab">
                                <div id="violations-list">
                                    <!-- Violations will be populated here -->
                                </div>
                            </div>
                            <div class="tab-pane fade" id="statistics-tab">
                                <div id="statistics-list">
                                    <!-- Statistics will be populated here -->
                                </div>
                            </div>
                            <div class="tab-pane fade" id="trends-tab">
                                <div class="row">
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="column-select">Column:</label>
                                            <select class="form-control" id="column-select">
                                                <!-- Columns will be populated here -->
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="statistic-select">Statistic:</label>
                                            <select class="form-control" id="statistic-select">
                                                <option value="count">Count</option>
                                                <option value="mean">Mean</option>
                                                <option value="median">Median</option>
                                                <option value="std">Standard Deviation</option>
                                                <option value="min">Minimum</option>
                                                <option value="max">Maximum</option>
                                            </select>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="form-group">
                                            <label for="days-select">Days:</label>
                                            <select class="form-control" id="days-select">
                                                <option value="7">7 days</option>
                                                <option value="30" selected>30 days</option>
                                                <option value="90">90 days</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <button class="btn btn-primary" onclick="showTrend()">Show Trend</button>
                                </div>
                                <div class="mt-3" id="trend-chart"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Load dashboard data on page load
        $(document).ready(function() {
            loadDashboard();
        });
        
        // Load dashboard data
        function loadDashboard() {
            $.ajax({
                url: '/api/dashboard',
                type: 'GET',
                success: function(data) {
                    updateDashboard(data);
                },
                error: function(error) {
                    console.error('Error loading dashboard:', error);
                }
            });
        }
        
        // Update dashboard with data
        function updateDashboard(data) {
            // Update last updated time
            $('#last-updated').text(data.last_updated);
            
            // Update summary metrics
            $('#tables-checked').text(data.tables_checked);
            $('#tables-with-issues').text(data.tables_with_issues);
            $('#total-violations').text(data.total_violations);
            
            // Update table list
            var tableList = $('#table-list');
            tableList.empty();
            
            data.tables.forEach(function(table) {
                var badgeClass = table.violations > 0 ? 'badge bg-danger' : 'badge bg-success';
                var badge = '<span class="' + badgeClass + '">' + table.violations + '</span>';
                var item = '<a href="#" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" onclick="showTableDetails(\'' + table.name + '\')">' + table.name + ' ' + badge + '</a>';
                tableList.append(item);
            });
            
            // Create violations by severity chart
            var violationsChart = document.getElementById('violations-chart');
            
            var chartData = [{
                type: 'pie',
                labels: ['High', 'Medium', 'Low'],
                values: [data.high_violations, data.medium_violations, data.low_violations],
                marker: {
                    colors: ['#dc3545', '#ffc107', '#28a745']
                },
                hole: 0.4
            }];
            
            var layout = {
                title: 'Violations by Severity',
                height: 300,
                margin: {l: 0, r: 0, b: 0, t: 40}
            };
            
            Plotly.newPlot(violationsChart, chartData, layout);
        }
        
        // Show table details
        function showTableDetails(tableName) {
            $('#table-name').text(tableName);
            $('#table-details-card').show();
            
            // Load table details
            $.ajax({
                url: '/api/table/' + tableName,
                type: 'GET',
                success: function(data) {
                    updateTableDetails(data);
                },
                error: function(error) {
                    console.error('Error loading table details:', error);
                }
            });
        }
        
        // Update table details
        function updateTableDetails(data) {
            // Update violations list
            var violationsList = $('#violations-list');
            violationsList.empty();
            
            if (data.violations.length === 0) {
                violationsList.html('<div class="alert alert-success">No violations found.</div>');
            } else {
                data.violations.forEach(function(violation, index) {
                    var severityClass = 'violation-' + violation.severity;
                    var card = '<div class="card mb-3 ' + severityClass + '">';
                    card += '<div class="card-header">' + violation.name + ' (' + violation.severity + ')</div>';
                    card += '<div class="card-body">';
                    card += '<p>' + violation.description + '</p>';
                    card += '<h6>Details:</h6>';
                    card += '<pre>' + JSON.stringify(violation.details, null, 2) + '</pre>';
                    card += '<h6>Remediation:</h6>';
                    card += '<p>' + violation.remediation.replace(/\\n/g, '<br>') + '</p>';
                    card += '</div></div>';
                    
                    violationsList.append(card);
                });
            }
            
            // Update statistics list
            var statisticsList = $('#statistics-list');
            statisticsList.empty();
            
            if (!data.statistics || Object.keys(data.statistics).length === 0) {
                statisticsList.html('<div class="alert alert-info">No statistics available.</div>');
            } else {
                var table = '<table class="table table-striped">';
                table += '<thead><tr><th>Column</th><th>Type</th><th>Count</th><th>Missing</th><th>Mean</th><th>Min</th><th>Max</th></tr></thead>';
                table += '<tbody>';
                
                Object.keys(data.statistics).forEach(function(column) {
                    var stats = data.statistics[column];
                    var type = typeof stats.mean !== 'undefined' ? 'Numeric' : 'Text';
                    
                    table += '<tr>';
                    table += '<td>' + column + '</td>';
                    table += '<td>' + type + '</td>';
                    table += '<td>' + (stats.count || 'N/A') + '</td>';
                    table += '<td>' + (stats.missing || 'N/A') + '</td>';
                    table += '<td>' + (stats.mean ? stats.mean.toFixed(2) : 'N/A') + '</td>';
                    table += '<td>' + (stats.min ? (typeof stats.min === 'number' ? stats.min.toFixed(2) : stats.min) : 'N/A') + '</td>';
                    table += '<td>' + (stats.max ? (typeof stats.max === 'number' ? stats.max.toFixed(2) : stats.max) : 'N/A') + '</td>';
                    table += '</tr>';
                });
                
                table += '</tbody></table>';
                statisticsList.append(table);
            }
            
            // Update column select for trends
            var columnSelect = $('#column-select');
            columnSelect.empty();
            
            if (data.statistics) {
                Object.keys(data.statistics).forEach(function(column) {
                    var stats = data.statistics[column];
                    if (typeof stats.mean !== 'undefined') {
                        columnSelect.append('<option value="' + column + '">' + column + '</option>');
                    }
                });
            }
        }
        
        // Show trend chart
        function showTrend() {
            var tableName = $('#table-name').text();
            var column = $('#column-select').val();
            var statistic = $('#statistic-select').val();
            var days = $('#days-select').val();
            
            if (!column) {
                alert('Please select a column');
                return;
            }
            
            // Load trend data
            $.ajax({
                url: '/api/trend/' + tableName + '/' + column,
                type: 'GET',
                data: {
                    statistic: statistic,
                    days: days
                },
                success: function(data) {
                    updateTrendChart(data, column, statistic);
                },
                error: function(error) {
                    console.error('Error loading trend data:', error);
                }
            });
        }
        
        // Update trend chart
        function updateTrendChart(data, column, statistic) {
            var trendChart = document.getElementById('trend-chart');
            
            if (!data.dates || data.dates.length === 0) {
                trendChart.innerHTML = '<div class="alert alert-info">No trend data available for this selection.</div>';
                return;
            }
            
            var chartData = [{
                type: 'scatter',
                mode: 'lines+markers',
                x: data.dates,
                y: data.values,
                line: {
                    color: '#007bff',
                    width: 2
                },
                marker: {
                    color: '#007bff',
                    size: 8
                }
            }];
            
            var layout = {
                title: statistic.charAt(0).toUpperCase() + statistic.slice(1) + ' Trend for ' + column,
                xaxis: {
                    title: 'Date'
                },
                yaxis: {
                    title: statistic.charAt(0).toUpperCase() + statistic.slice(1)
                },
                height: 400,
                margin: {l: 50, r: 50, b: 50, t: 50}
            };
            
            Plotly.newPlot(trendChart, chartData, layout);
        }
        
        // Run quality check
        function runCheck() {
            if (!confirm('Run quality check on all tables?')) {
                return;
            }
            
            $.ajax({
                url: '/api/check',
                type: 'POST',
                success: function(data) {
                    alert('Quality check completed. Found ' + data.total_violations + ' violations.');
                    loadDashboard();
                },
                error: function(error) {
                    console.error('Error running quality check:', error);
                    alert('Error running quality check');
                }
            });
        }
        
        // Generate report
        function generateReport() {
            if (!confirm('Generate quality report?')) {
                return;
            }
            
            $.ajax({
                url: '/api/report',
                type: 'POST',
                success: function(data) {
                    if (data.report_path) {
                        alert('Report generated: ' + data.report_path);
                        window.open('/report/' + data.report_filename, '_blank');
                    } else {
                        alert('Error generating report');
                    }
                },
                error: function(error) {
                    console.error('Error generating report:', error);
                    alert('Error generating report');
                }
            });
        }
    </script>
</body>
</html>""")

# Initialize dashboard data
dashboard_data = {
    "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "tables_checked": 0,
    "tables_with_issues": 0,
    "total_violations": 0,
    "high_violations": 0,
    "medium_violations": 0,
    "low_violations": 0,
    "tables": []
}

# Initialize table data
table_data = {}

# Initialize monitor
def init_monitor():
    global monitor
    if monitor is None:
        monitor = DataQualityMonitor()

# Route for dashboard
@app.route('/')
def index():
    return render_template('index.html')

# API route for dashboard data
@app.route('/api/dashboard')
def api_dashboard():
    init_monitor()
    global dashboard_data
    
    # Update last updated time
    dashboard_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return jsonify(dashboard_data)

# API route for table details
@app.route('/api/table/<table_name>')
def api_table(table_name):
    init_monitor()
    global table_data
    
    # Return cached data if available
    if table_name in table_data:
        return jsonify(table_data[table_name])
        
    # Get table details
    if monitor.conn is None:
        return jsonify({"error": "No database connection"})
        
    try:
        # Get table data
        query = f"SELECT * FROM {table_name} LIMIT 1000"
        df = pd.read_sql(query, monitor.conn)
        
        if len(df) == 0:
            return jsonify({"error": f"No data in table {table_name}"})
            
        # Get statistics
        statistics = monitor.calculate_statistics(table_name)
        
        # Get violations
        check = monitor.check_table(table_name)
        violations = [rule.to_dict() for rule in check.violations]
        
        # Cache data
        table_data[table_name] = {
            "name": table_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": df.columns.tolist(),
            "statistics": statistics,
            "violations": violations
        }
        
        return jsonify(table_data[table_name])
        
    except Exception as e:
        logger.error(f"Error getting table details: {e}")
        return jsonify({"error": str(e)})

# API route for trend data
@app.route('/api/trend/<table_name>/<column>')
def api_trend(table_name, column):
    init_monitor()
    
    # Get parameters
    statistic = request.args.get('statistic', 'count')
    days = int(request.args.get('days', 30))
    
    # Define time period
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get statistics history
    stats_history = monitor._get_statistics_history(table_name, column, start_date, end_date)
    
    if not stats_history:
        return jsonify({"error": f"No statistics history for {table_name}.{column}"})
        
    # Extract dates and values
    dates = []
    values = []
    
    for item in stats_history:
        if statistic in item["stats"]:
            dates.append(item["timestamp"])
            values.append(item["stats"][statistic])
            
    if not dates:
        return jsonify({"error": f"No {statistic} data for {table_name}.{column}"})
        
    return jsonify({
        "table": table_name,
        "column": column,
        "statistic": statistic,
        "dates": dates,
        "values": values
    })

# API route for running quality check
@app.route('/api/check', methods=['POST'])
def api_check():
    init_monitor()
    global dashboard_data, table_data
    
    # Check all tables
    results = monitor.check_all_tables()
    
    if not results:
        return jsonify({"error": "No tables checked"})
        
    # Update dashboard data
    dashboard_data["tables_checked"] = len(results)
    dashboard_data["tables_with_issues"] = sum(1 for check in results.values() if check.violations)
    dashboard_data["total_violations"] = sum(len(check.violations) for check in results.values())
    
    # Count violations by severity
    high_violations = 0
    medium_violations = 0
    low_violations = 0
    
    for check in results.values():
        for rule in check.violations:
            if rule.severity == "high":
                high_violations += 1
            elif rule.severity == "medium":
                medium_violations += 1
            else:
                low_violations += 1
                
    dashboard_data["high_violations"] = high_violations
    dashboard_data["medium_violations"] = medium_violations
    dashboard_data["low_violations"] = low_violations
    
    # Update table data
    dashboard_data["tables"] = []
    
    for table, check in results.items():
        table_data[table] = {
            "name": table,
            "violations": len(check.violations)
        }
        
        dashboard_data["tables"].append({
            "name": table,
            "violations": len(check.violations)
        })
        
    # Clear cache
    table_data = {}
    
    return jsonify({
        "success": True,
        "tables_checked": dashboard_data["tables_checked"],
        "tables_with_issues": dashboard_data["tables_with_issues"],
        "total_violations": dashboard_data["total_violations"]
    })

# API route for generating report
@app.route('/api/report', methods=['POST'])
def api_report():
    init_monitor()
    
    # Generate report
    report_path = monitor.generate_quality_report()
    
    if report_path:
        # Get report filename
        report_filename = os.path.basename(report_path)
        
        return jsonify({
            "success": True,
            "report_path": report_path,
            "report_filename": report_filename
        })
    else:
        return jsonify({"error": "Failed to generate report"})

# Route for viewing reports
@app.route('/report/<path:filename>')
def report(filename):
    return send_from_directory(monitor.history_dir, filename)

# Route for static files
@app.route('/static/<path:filename>')
def static_file(filename):
    return send_from_directory(static_dir, filename)

# Main function
def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Data Quality Dashboard")
    parser.add_argument("--host", default="127.0.0.1", help="Host to run dashboard on")
    parser.add_argument("--port", type=int, default=5000, help="Port to run dashboard on")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    
    args = parser.parse_args()
    
    # Initialize monitor
    init_monitor()
    
    # Run dashboard
    app.run(host=args.host, port=args.port, debug=args.debug)

if __name__ == "__main__":
    import argparse
    main()