import sys
import os

# Ensure imports work correctly when script is in task_solution
# and run from task_solution directory.
# Add the parent directory of 'agents' to sys.path if 'agents' is not found directly
# This handles running from task_solution or from repository root if needed for subtask context
# current_dir = os.path.dirname(os.path.abspath(__file__)) # This is task_solution
# project_root = os.path.dirname(current_dir) # This would be one level above task_solution

from agents.report_maker.time_table_maker import TimeTable, TimeTableList
from agents.report_maker.report_maker import ReportInfo, Reference

# Helper function to create a dummy ReportInfo object
def create_dummy_report_info():
    return ReportInfo(
        title="テストレポート",
        abstract="これはテストレポートの概要です。",
        done_tasks=["タスク1完了", "タスク2完了"],
        problems=["特になし"],
        feedback="テストは順調です。",
        references=[Reference(title="参考資料1", url="http://example.com")]
    )

def test_chart_with_multiple_types_including_rest():
    print("\n--- Test: Multiple types including Rest ---")
    sample_entries = [
        TimeTable(task_type="開発作業", start_time="09:00", end_time="11:00"),
        TimeTable(task_type="顧客ミーティング", start_time="11:00", end_time="11:30"),
        TimeTable(task_type="休憩", start_time="12:00", end_time="13:00"), # "休憩" should be included
        TimeTable(task_type="市場調査", start_time="14:00", end_time="15:30"),
        TimeTable(task_type="離席", start_time="15:30", end_time="16:00"), # "離席" should be excluded
    ]
    time_table_list = TimeTableList(time_table=sample_entries)
    report_info = create_dummy_report_info()

    # Verify get_task_types_for_chart
    chart_task_types = time_table_list.get_task_types_for_chart()
    assert "開発作業" in chart_task_types
    assert "顧客ミーティング" in chart_task_types
    assert "休憩" in chart_task_types # Crucial: Rest is IN
    assert "市場調査" in chart_task_types
    assert "離席" not in chart_task_types # Crucial: Away is OUT
    print(f"Chart task types: {chart_task_types.keys()} - Correct.")

    # Verify chart generation and markdown output
    markdown_output = report_info.to_markdown(time_table_list)
    # print(f"Markdown for multiple types (incl. Rest):\n{markdown_output}")
    assert "![作業時間割合の円グラフ](/static/generated_charts/pie_chart_" in markdown_output
    assert "休憩" in markdown_output # Check if "休憩" is mentioned, likely in the chart labels or durations
    assert "離席" not in markdown_output or "離席: " not in time_table_list.total_duration_by_type() #離席は作業時間集計にも出ない想定
    print("SUCCESS: Chart generated for multiple types including '休憩', '離席' excluded.")

    # Verify file creation (optional, as markdown check is primary)
    chart_image_path_in_md = markdown_output.split("![作業時間割合の円グラフ](")[1].split(")")[0]
    # Assuming CWD is repo root (/app), and chart_image_path_in_md is like "/static/..."
    # We need to check "task_solution/static/..."
    path_to_check = os.path.join("task_solution", chart_image_path_in_md.lstrip('/'))
    assert os.path.exists(path_to_check), f"Chart file {path_to_check} not found."
    print(f"Chart file {path_to_check} exists.")


def test_chart_with_single_task_type():
    print("\n--- Test: Single task type (e.g., Development only) ---")
    sample_entries = [
        TimeTable(task_type="開発作業", start_time="09:00", end_time="17:00"),
    ]
    time_table_list = TimeTableList(time_table=sample_entries)
    report_info = create_dummy_report_info()

    chart_task_types = time_table_list.get_task_types_for_chart()
    assert len(chart_task_types) == 1
    assert "開発作業" in chart_task_types
    print(f"Chart task types: {chart_task_types.keys()} - Correct (single).")

    markdown_output = report_info.to_markdown(time_table_list)
    # print(f"Markdown for single type:\n{markdown_output}")
    assert "![作業時間割合の円グラフ]" not in markdown_output # No image tag
    assert "（グラフは作業種別が複数の場合にのみ表示されます）" in markdown_output
    print("SUCCESS: Chart NOT generated for single task type, message shown.")

def test_chart_with_only_rest_task_type():
    print("\n--- Test: Single task type (Rest only) ---")
    sample_entries = [
        TimeTable(task_type="休憩", start_time="12:00", end_time="13:00"),
    ]
    time_table_list = TimeTableList(time_table=sample_entries)
    report_info = create_dummy_report_info()

    chart_task_types = time_table_list.get_task_types_for_chart()
    assert len(chart_task_types) == 1
    assert "休憩" in chart_task_types
    print(f"Chart task types: {chart_task_types.keys()} - Correct (single '休憩').")

    markdown_output = report_info.to_markdown(time_table_list)
    # print(f"Markdown for Rest only:\n{markdown_output}")
    assert "![作業時間割合の円グラフ]" not in markdown_output
    assert "（グラフは作業種別が複数の場合にのみ表示されます）" in markdown_output
    print("SUCCESS: Chart NOT generated for '休憩' only, message shown.")


def test_chart_with_only_away_task_type():
    print("\n--- Test: Single task type (Away only) ---")
    # This case should result in "no data" because "離席" is always excluded.
    sample_entries = [
        TimeTable(task_type="離席", start_time="12:00", end_time="13:00"),
    ]
    time_table_list = TimeTableList(time_table=sample_entries)
    report_info = create_dummy_report_info()

    chart_task_types = time_table_list.get_task_types_for_chart()
    assert len(chart_task_types) == 0
    print(f"Chart task types: {chart_task_types.keys()} - Correct (empty as '離席' is excluded).")

    markdown_output = report_info.to_markdown(time_table_list)
    # print(f"Markdown for Away only:\n{markdown_output}")
    assert "![作業時間割合の円グラフ]" not in markdown_output
    assert "（表示対象の作業時間データがありません）" in markdown_output # Different message
    print("SUCCESS: Chart NOT generated for '離席' only, 'no data' message shown.")

def test_chart_with_no_task_entries():
    print("\n--- Test: No task entries ---")
    sample_entries = []
    time_table_list = TimeTableList(time_table=sample_entries)
    report_info = create_dummy_report_info()

    chart_task_types = time_table_list.get_task_types_for_chart()
    assert len(chart_task_types) == 0
    print(f"Chart task types: {chart_task_types.keys()} - Correct (empty).")

    markdown_output = report_info.to_markdown(time_table_list)
    # print(f"Markdown for no entries:\n{markdown_output}")
    assert "![作業時間割合の円グラフ]" not in markdown_output
    assert "（表示対象の作業時間データがありません）" in markdown_output
    print("SUCCESS: Chart NOT generated for no entries, 'no data' message shown.")


def run_all_tests():
    print("Starting all chart generation tests...")
    print(f"Current working directory during test: {os.getcwd()}") # Should be /app (repo root)

    # Ensure the generated_charts directory exists for file creation checks
    # This should point to task_solution/static/generated_charts from repo root
    charts_dir_to_ensure = os.path.join("task_solution", "static", "generated_charts")
    if not os.path.exists(charts_dir_to_ensure):
        os.makedirs(charts_dir_to_ensure)
        print(f"Created directory: {charts_dir_to_ensure}")

    test_chart_with_multiple_types_including_rest()
    test_chart_with_single_task_type()
    test_chart_with_only_rest_task_type()
    test_chart_with_only_away_task_type()
    test_chart_with_no_task_entries()

    print("\nAll chart generation tests finished.")

if __name__ == "__main__":
    # Add project root to sys.path to allow imports from agents module
    # This is necessary if test_chart_generation.py is run directly from task_solution
    # and agents is a sibling directory.
    # current_dir = os.path.dirname(os.path.abspath(__file__)) # task_solution
    # project_root = os.path.dirname(current_dir) # One level up
    # sys.path.insert(0, project_root)
    # No, the instruction is to run from `task_solution`, so `agents` should be directly importable.

    # If running from repository root (e.g., via a script), this might be needed:
    # if "task_solution" not in os.getcwd():
    #     os.chdir("task_solution")
    #     print(f"Changed CWD to: {os.getcwd()}")

    # The problem states the CWD will be task_solution, so direct imports are fine.
    # We need to handle the path for `matplotlib.font_manager` if it tries to write cache.
    # This usually goes to ~/.matplotlib. If sandbox has no write access there, it might fail.
    # However, font downloading is to a local `temp_fonts` dir.

    # Make sure `temp_fonts` directory exists before `TimeTableList` tries to use it.
    # (Though `TimeTableList` itself creates it, good to be defensive in tests if needed)
    # base_dir_for_fonts = os.path.dirname(os.path.abspath(__file__)) # task_solution
    # temp_font_dir_for_tests = os.path.join(base_dir_for_fonts, "temp_fonts")
    # os.makedirs(temp_font_dir_for_tests, exist_ok=True)

    run_all_tests()
