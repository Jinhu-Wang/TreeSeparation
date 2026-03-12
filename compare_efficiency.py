"""
TreeSeparation Efficiency Comparator
Compares the execution time of Sequential vs. Parallel implementations.
Saves results to a text file and a PNG chart.
"""

import sys
import os
import subprocess
import re
import time
import statistics

def check_files_exist(seq_script, par_script):
    """Verifies that the necessary scripts exist."""
    missing = []
    if not os.path.exists(seq_script):
        missing.append(seq_script)
    if not os.path.exists(par_script):
        missing.append(par_script)
    
    if missing:
        print("Error: Could not find the following scripts in the current directory:")
        for m in missing:
            print(f"  - {m}")
        print("Please ensure both scripts are saved with these names.")
        sys.exit(1)

def run_and_parse(script_name, label, regex_filename, regex_time):
    """
    Runs a python script via subprocess, captures stdout, 
    and parses filenames and execution times using provided regex.
    """
    print(f"\n--- Running {label} Implementation ({script_name}) ---")
    print("This may take a while depending on dataset size...")
    
    start_time = time.time()
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error occurred while running {script_name}:")
        print(e.stderr)
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}

    elapsed = time.time() - start_time
    print(f"Finished {label} run in {elapsed:.2f} seconds.")
    
    # Parse Output
    output = result.stdout
    data = {}
    
    lines = output.split('\n')
    current_file = None
    
    for line in lines:
        line = line.strip()
        
        # 1. Look for Filename
        file_match = re.search(regex_filename, line)
        if file_match:
            current_file = file_match.group(1).strip()
            continue
            
        # 2. Look for Time
        time_match = re.search(regex_time, line)
        if time_match and current_file:
            duration = float(time_match.group(1))
            data[current_file] = duration
            
    return data

def generate_report(seq_data, par_data, report_file, chart_file):
    """Generates a text report to file and saves a plot."""
    print(f"\nGenerating report...")
    
    # Find common files processed by both
    common_files = sorted(set(seq_data.keys()).intersection(par_data.keys()))
    
    if not common_files:
        print("No matching files found in the output of both scripts.")
        return

    # --- 1. Generate Text Report ---
    lines = []
    lines.append("="*80)
    lines.append(f"{'PERFORMANCE COMPARISON REPORT':^80}")
    lines.append("="*80)
    lines.append(f"{'Filename':<30} | {'Sequential (s)':<15} | {'Parallel (s)':<15} | {'Speedup':<10}")
    lines.append("-" * 80)
    
    speedups = []
    
    for fname in common_files:
        t_seq = seq_data[fname]
        t_par = par_data[fname]
        
        if t_par > 0:
            speedup = t_seq / t_par
            speedups.append(speedup)
        else:
            speedup = 0.0
            
        lines.append(f"{fname:<30} | {t_seq:<15.4f} | {t_par:<15.4f} | {speedup:<10.2f}x")
        
    lines.append("-" * 80)
    
    if speedups:
        avg_speedup = statistics.mean(speedups)
        lines.append(f"Average Speedup: {avg_speedup:.2f}x")
        if avg_speedup > 1.0:
            lines.append(f"Conclusion: Parallel version is {avg_speedup:.2f} times faster on average.")
        else:
            lines.append("Conclusion: Parallel version provided no benefit (dataset might be too small).")
    
    # Write to file
    try:
        with open(report_file, "w") as f:
            f.write("\n".join(lines))
        print(f"Successfully saved report to: {report_file}")
        
        # Also print to console
        print("\n".join(lines))
    except Exception as e:
        print(f"Error writing report file: {e}")

    # --- 2. Generate and Save Chart ---
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        
        indices = np.arange(len(common_files))
        width = 0.35
        
        seq_times = [seq_data[f] for f in common_files]
        par_times = [par_data[f] for f in common_files]
        
        fig, ax = plt.subplots(figsize=(12, 7))
        rects1 = ax.bar(indices - width/2, seq_times, width, label='Sequential', color='salmon', alpha=0.8)
        rects2 = ax.bar(indices + width/2, par_times, width, label='Parallel', color='skyblue', alpha=0.8)
        
        ax.set_ylabel('Time (seconds)')
        ax.set_title('Tree Separation Efficiency: Sequential vs Parallel')
        ax.set_xticks(indices)
        ax.set_xticklabels(common_files, rotation=45, ha='right')
        ax.legend()
        
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(chart_file, dpi=300)
        plt.close()
        print(f"Successfully saved chart to: {chart_file}")
        
    except ImportError:
        print("\n[Info] Install 'matplotlib' to generate the chart (pip install matplotlib).")
    except Exception as e:
        print(f"\n[Info] Could not generate plot: {e}")

if __name__ == "__main__":
    # =========================================================
    #                     CONFIGURATION
    # =========================================================
    
    # Names of the scripts to compare
    SCRIPT_SEQ = "tree_ind.py"
    SCRIPT_PAR = "tree_ind_parallelized.py"

    # Output filenames
    OUTPUT_REPORT_FILE = "efficiency_report.txt"
    OUTPUT_CHART_FILE = "efficiency_chart.png"

    # --- REGEX PATTERNS ---
    # Matches filename in both scripts (looks for "Processing: filename.xyz")
    REGEX_FILENAME = r"Processing:\s+([^\s|]+)"

    # Matches TIME in EITHER script format:
    # Seq: "Total File Time:   33.3700 sec"
    # Par: "[Time] TOTAL for file: 12.3400 sec"
    REGEX_TIME = r"(?:Total File Time:|\[Time\] TOTAL for file:)\s+([\d\.]+)\s+sec"

    # =========================================================
    #                   MAIN EXECUTION
    # =========================================================

    check_files_exist(SCRIPT_SEQ, SCRIPT_PAR)
    
    # Run Sequential
    seq_results = run_and_parse(SCRIPT_SEQ, "Sequential", REGEX_FILENAME, REGEX_TIME)
    
    if not seq_results:
        print("Sequential script produced no valid output results. Exiting.")
        sys.exit(1)
        
    # Run Parallel
    par_results = run_and_parse(SCRIPT_PAR, "Parallel", REGEX_FILENAME, REGEX_TIME)
    
    if not par_results:
        print("Parallel script produced no valid output results. Exiting.")
        sys.exit(1)
        
    # Generate Files
    generate_report(seq_results, par_results, OUTPUT_REPORT_FILE, OUTPUT_CHART_FILE)
