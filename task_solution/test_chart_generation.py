import sys
import os

# Ensure imports work correctly when script is in task_solution
# and run from task_solution directory.
# Add the parent directory of 'agents' to sys.path if 'agents' is not found directly
# This handles running from task_solution or from repository root if needed for subtask context
# current_dir = os.path.dirname(os.path.abspath(__file__)) # This is task_solution
# project_root = os.path.dirname(current_dir) # This would be one level above task_solution

# The instruction is to run from task_solution directory, so direct imports should be fine.
from agents.report_maker.time_table_maker import TimeTable, TimeTableList
from agents.report_maker.report_maker import ReportInfo, Reference

def run_test():
    print("Starting chart generation test...")
    # The test is to be run from task_solution directory.
    # File paths for chart generation are relative to time_table_maker.py,
    # which is task_solution/agents/report_maker/time_table_maker.py
    # So, os.path.join(os.path.dirname(__file__), "..", "..", "static", "generated_charts")
    # from time_table_maker.py becomes:
    # task_solution/agents/report_maker/../../static/generated_charts
    # = task_solution/static/generated_charts

    # 1. Create Sample TimeTable data
    sample_time_entries = [
        TimeTable(task_type="開発作業", start_time="09:00", end_time="11:00"), # "Development Work"
        TimeTable(task_type="顧客ミーティング", start_time="11:00", end_time="11:30"), # "Client Meeting"
        TimeTable(task_type="休憩時間", start_time="12:00", end_time="13:00"), # "Rest Time" (should be excluded from chart)
        TimeTable(task_type="市場調査", start_time="14:00", end_time="15:30"), # "Market Research"
        TimeTable(task_type="開発作業", start_time="15:30", end_time="17:00"), # "Development Work"
    ]
    # Expected chart data (with Japanese labels): 開発作業, 顧客ミーティング, 市場調査
    time_table_list = TimeTableList(time_table=sample_time_entries)

    # 2. Create dummy ReportInfo
    report_info = ReportInfo(
        title="テストレポート",
        abstract="これはテストレポートの概要です。",
        done_tasks=["タスク1完了", "タスク2完了"],
        problems=["特になし"],
        feedback="テストは順調です。",
        references=[Reference(title="参考資料1", url="http://example.com")]
    )

    # 3. Generate chart path (for verification of creation and path)
    # This path is what to_markdown will eventually use.
    # Test script is in task_solution, CWD will be task_solution
    print(f"Current working directory during test: {os.getcwd()}")

    # The generate_pie_chart_path method builds path like:
    # charts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static", "generated_charts")
    # where __file__ is time_table_maker.py. So path is relative from there.
    # It correctly resolves to task_solution/static/generated_charts

    chart_path_for_markdown_display = time_table_list.generate_pie_chart_path() # This is the URL like /static/...
    print(f"Generated chart URL for Markdown: {chart_path_for_markdown_display}")

    if chart_path_for_markdown_display:
        # The path returned is like "/static/generated_charts/pie_chart_uuid.png"
        # To check for file existence, we need a path relative to CWD (task_solution)
        # So, "static/generated_charts/pie_chart_uuid.png"
        relative_chart_file_path = chart_path_for_markdown_display.lstrip('/')
        # actual_chart_file_path = os.path.join(os.getcwd(), relative_chart_file_path) # This would be task_solution/static/...
        # Simpler: just use the relative path directly if CWD is task_solution

        print(f"Expecting chart file relative to CWD (task_solution): {relative_chart_file_path}")

        if os.path.exists(relative_chart_file_path):
            print(f"SUCCESS: Chart image file successfully created at: {relative_chart_file_path} (relative to CWD)")
        else:
            print(f"ERROR: Chart image file NOT found at: {relative_chart_file_path} (relative to CWD)")
            # For debugging, list contents of the expected directory
            charts_dir = os.path.join("static", "generated_charts") # Relative to CWD
            if os.path.exists(charts_dir):
                print(f"Contents of {charts_dir}: {os.listdir(charts_dir)}")
            else:
                print(f"Directory {charts_dir} does not exist.")
    elif not chart_path_for_markdown_display and any(t.task_type not in ["休憩", "離席"] for t in time_table_list.time_table):
        print("ERROR: Chart path is empty, but there was data to plot. Chart generation might have failed.")
    elif not any(t.task_type not in ["休憩", "離席"] for t in time_table_list.time_table):
        print("INFO: No chart generated as there were no time entries (or only excluded ones).")


    # 4. Generate Markdown (this will also call generate_pie_chart_path internally again, creating a *new* chart)
    markdown_output = report_info.to_markdown(time_table_list)
    print("\n--- Markdown Output ---")
    print(markdown_output)
    print("--- End of Markdown Output ---\n")

    # Check the image path in the markdown output
    if chart_path_for_markdown_display and chart_path_for_markdown_display in markdown_output:
        print(f"SUCCESS: Chart path {chart_path_for_markdown_display} found in Markdown output.")
    elif chart_path_for_markdown_display:
        print(f"WARNING: The specific chart path {chart_path_for_markdown_display} (from first call) was not found in Markdown. A new chart was generated. This is expected.")
        if "/static/generated_charts/pie_chart_" in markdown_output:
             print("INFO: A new chart path like /static/generated_charts/pie_chart_... was found in markdown output as expected.")
        else:
             print("ERROR: No chart path found in markdown output.")


    print("Test finished.")

if __name__ == "__main__":
    run_test()
