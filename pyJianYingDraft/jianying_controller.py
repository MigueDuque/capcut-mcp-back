"""JianYing automation controller, primarily for auto-export"""

import time
import shutil
from process_controller import ProcessController
import uiautomation as uia
import re
import os
from logging.handlers import RotatingFileHandler
import logging  # Import logging module

from enum import Enum
from typing import Optional, Literal, Callable

from . import exceptions
from .exceptions import AutomationError

# --- Configure logger ---
logger = logging.getLogger('fastapi_video_generator')  # Define a specific logger name for the FastAPI app
logger.setLevel(logging.INFO)  # Set minimum logging level

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Create a console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Create a file handler with log rotation
log_dir = 'logs'  # Log file directory
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_file_path = os.path.join(log_dir, 'fastapi_video_generator.log')  # Log file name

file_handler = RotatingFileHandler(log_file_path, backupCount=5, encoding='utf-8')  # 5MB per file, keep 5 backups
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

logger.info("FastAPI application logging system initialized.")

class Export_resolution(Enum):
    """Export resolution"""
    RES_4K = "4K"
    RES_2K = "2K"
    RES_1080P = "1080P"
    RES_720P = "720P"
    RES_480P = "480P"

class Export_framerate(Enum):
    """Export framerate"""
    FR_24 = "24fps"
    FR_25 = "25fps"
    FR_30 = "30fps"
    FR_50 = "50fps"
    FR_60 = "60fps"

class ControlFinder:
    """Control finder; encapsulates control-lookup logic"""

    @staticmethod
    def desc_matcher(target_desc: str, depth: int = 2, exact: bool = False) -> Callable[[uia.Control, int], bool]:
        """Matcher that finds controls by full_description"""
        target_desc = target_desc.lower()
        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            full_desc: str = control.GetPropertyValue(30159).lower()
            return (target_desc == full_desc) if exact else (target_desc in full_desc)
        return matcher

    @staticmethod
    def class_name_matcher(class_name: str, depth: int = 1, exact: bool = False) -> Callable[[uia.Control, int], bool]:
        """Matcher that finds controls by ClassName"""
        class_name = class_name.lower()
        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            curr_class_name: str = control.ClassName.lower()
            return (class_name == curr_class_name) if exact else (class_name in curr_class_name)
        return matcher

class Jianying_controller:
    """JianYing automation controller"""

    app: uia.WindowControl
    """JianYing window handle"""
    app_status: Literal["home", "edit", "pre_export"]
    export_progress: dict = {"status": "idle", "percent": 0.0, "message": "", "start_time": 0}
    """Export progress info"""

    def __init__(self):
        """Initialize the JianYing controller; JianYing must be on the home page at this point"""
        logger.info("Initializing Jianying_controller...")
        self.get_window()
        self.export_progress = {"status": "idle", "percent": 0.0, "message": "", "start_time": 0}
        logger.info("Jianying_controller initialized successfully.")

    def get_export_progress(self) -> dict:
        """Get the current export progress.

        Returns:
            dict: A dictionary with the following fields:
                - status: Current status; one of "idle", "exporting", "finished", "error"
                - percent: Export progress percentage, a float in [0, 100]
                - message: Progress message
                - start_time: Timestamp when the export started
                - elapsed: Time elapsed in seconds
        """
        if self.export_progress["status"] != "idle":
            self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
        return self.export_progress

    def export_draft(self, draft_name: str, output_path: Optional[str] = None, *,
                     resolution: Optional[Export_resolution] = None,
                     framerate: Optional[Export_framerate] = None,
                     timeout: float = 1200) -> None:
        """Export the specified JianYing draft — **currently only supports JianYing 6 and below**

        **Note: the account must have export permission (no VIP-required features, or VIP is active),
        otherwise the process may enter an infinite loop.**

        Args:
            draft_name (`str`): Name of the JianYing draft to export.
            output_path (`str`, optional): Output path; can point to a folder or a file.
                If omitted, JianYing's default export path is used.
            resolution (`Export_resolution`, optional): Export resolution; defaults to the current
                setting in the JianYing export window.
            framerate (`Export_framerate`, optional): Export framerate; defaults to the current
                setting in the JianYing export window.
            timeout (`float`, optional): Export timeout in seconds. Defaults to 20 minutes.

        Raises:
            `DraftNotFound`: No draft with the given name was found.
            `AutomationError`: A UI automation operation failed.
        """
        logger.info(f"Starting export for draft: '{draft_name}' to '{output_path or 'default path'}' with resolution: {resolution}, framerate: {framerate}")
        self.export_progress["status"] = "exporting"
        self.export_progress["percent"] = 0.0
        self.export_progress["message"] = "Starting export"
        self.export_progress["start_time"] = time.time()
        self.export_progress["elapsed"] = 0

        logger.info("Attempting to switch to home page.")
        self.get_window()
        self.switch_to_home()
        logger.info("Successfully switched to home page.")

        self.export_progress["status"] = "exporting"
        self.export_progress["percent"] = 5.0
        self.export_progress["message"] = "Exporting"
        self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]

        logger.info(f"Clicking draft: '{draft_name}'")
        # Click the target draft
        draft_name_text = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher(f"HomePageDraftTitle:{draft_name}", exact=True)
        )
        if not draft_name_text.Exists(0):
            error_msg = f"DraftNotFound: No Jianying draft named '{draft_name}' found."
            logger.error(error_msg)
            self.export_progress["status"] = "error"
            self.export_progress["percent"] = 100.0
            self.export_progress["message"] = f"No JianYing draft named '{draft_name}' found"
            self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
            raise exceptions.DraftNotFound(f"No JianYing draft named '{draft_name}' found")
        draft_btn = draft_name_text.GetParentControl()
        if draft_btn is None:
            error_msg = f"AutomationError: Could not find parent control for draft title '{draft_name}'."
            logger.error(error_msg)
            self.export_progress["status"] = "error"
            self.export_progress["percent"] = 100.0
            self.export_progress["message"] = f"Automation failed: cannot click draft '{draft_name}'"
            self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
            raise AutomationError(error_msg)

        draft_btn.Click(simulateMove=False)
        logger.info(f"Clicked on draft: '{draft_name}'.")

        self.export_progress["status"] = "exporting"
        self.export_progress["percent"] = 10.0
        self.export_progress["message"] = "Exporting"
        self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]

        logger.info(f"Waiting for edit window for draft: '{draft_name}' (timeout: 180s)")
        # Wait for the edit window to load, up to 180 seconds
        wait_start_time = time.time()
        while time.time() - wait_start_time < 180:
            try:
                self.get_window()  # Attempt to refresh the window handle and status
            except AutomationError as e:
                logger.debug(f"Failed to get window during edit window wait: {e}. Retrying...")
                time.sleep(1)
                continue

            # Check for GPU environment prompt and dismiss it if present
            try:
                disable_btn = self.app.TextControl(searchDepth=3, Compare=ControlFinder.desc_matcher("暂不启用"))
                if disable_btn.Exists(0):
                    disable_btn.Click(simulateMove=False)
                    logger.info("Clicked '暂不启用' for graphics environment prompt.")
                    time.sleep(1)
            except Exception as e:
                logger.debug(f"No '暂不启用' button found or error during click: {e}")

            # Check if the edit window is active
            time.sleep(1)
            export_btn = self.app.TextControl(searchDepth=2, Compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn"))
            if export_btn.Exists(0):
                time.sleep(1)
                break
            time.sleep(1)
        else:
            error_msg = f"AutomationError: Waiting for edit window timed out (180 seconds) for draft '{draft_name}'."
            logger.error(error_msg)
            self.export_progress["status"] = "error"
            self.export_progress["percent"] = 100.0
            self.export_progress["message"] = "Edit window load timed out (180s)"
            self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
            raise AutomationError("Timed out waiting for edit window (180 seconds)")
        self.export_progress["status"] = "exporting"
        self.export_progress["percent"] = 15.0
        self.export_progress["message"] = "Exporting"
        self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]

        # Click the export button
        export_btn.Click(simulateMove=False)

        logger.info(f"Waiting for export settings window (timeout: 180s) for draft: '{draft_name}'")
        # Wait for the export settings window to load, up to 180 seconds
        wait_start_time = time.time()
        while time.time() - wait_start_time < 180:
            try:
                self.get_window()
            except:
                time.sleep(1)
                continue
            # Check if the export settings window is active
            export_path_sib = self.app.TextControl(searchDepth=2, Compare=ControlFinder.desc_matcher("ExportPath"))
            if export_path_sib.Exists(0):
                time.sleep(1)  # Extra wait to ensure UI is stable
                break
            time.sleep(1)
        else:
            self.export_progress["status"] = "error"
            self.export_progress["percent"] = 100.0
            self.export_progress["message"] = "Export settings window timed out (180s)"
            self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
            raise AutomationError("Timed out waiting for export settings window (180 seconds)")
        self.export_progress["status"] = "exporting"
        self.export_progress["percent"] = 20.0
        self.export_progress["message"] = "Exporting"
        self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]

        # Read the original export path (including file extension)
        export_path_text = export_path_sib.GetSiblingControl(lambda ctrl: True)
        assert export_path_text is not None
        export_path = export_path_text.GetPropertyValue(30159)

        logger.info(f"Attempting to set resolution: {resolution.value if resolution else 'unchanged'}, framerate: {framerate.value if framerate else 'unchanged'} for '{draft_name}'")
        # Set resolution
        if resolution is not None:
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    setting_group = self.app.GroupControl(searchDepth=1,
                                                      Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"))
                    if not setting_group.Exists(0):
                        raise AutomationError("Export settings group not found")
                    resolution_btn = setting_group.TextControl(searchDepth=2, Compare=ControlFinder.desc_matcher("ExportSharpnessInput"))
                    if not resolution_btn.Exists(0.5):
                        raise AutomationError("Export resolution dropdown not found")
                    resolution_btn.Click(simulateMove=False)
                    time.sleep(0.5)
                    resolution_item = self.app.TextControl(
                        searchDepth=2, Compare=ControlFinder.desc_matcher(resolution.value)
                    )
                    if not resolution_item.Exists(0.5):
                        raise AutomationError(f"Resolution option '{resolution.value}' not found")
                    resolution_item.Click(simulateMove=False)
                    time.sleep(0.5)
                    break  # Success, exit retry loop
                except AutomationError as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise  # Retries exhausted, re-raise
                    time.sleep(1)  # Wait 1 second before retrying

        # Set framerate
        if framerate is not None:
            retry_count = 0
            max_retries = 3
            while retry_count < max_retries:
                try:
                    setting_group = self.app.GroupControl(searchDepth=1,
                                                      Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"))
                    if not setting_group.Exists(0):
                        raise AutomationError("Export settings group not found")
                    framerate_btn = setting_group.TextControl(searchDepth=2, Compare=ControlFinder.desc_matcher("FrameRateInput"))
                    if not framerate_btn.Exists(0.5):
                        raise AutomationError("Export framerate dropdown not found")
                    framerate_btn.Click(simulateMove=False)
                    time.sleep(0.5)
                    framerate_item = self.app.TextControl(
                        searchDepth=2, Compare=ControlFinder.desc_matcher(framerate.value)
                    )
                    if not framerate_item.Exists(0.5):
                        raise AutomationError(f"Framerate option '{framerate.value}' not found")
                    framerate_item.Click(simulateMove=False)
                    time.sleep(0.5)
                    break  # Success, exit retry loop
                except AutomationError as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise  # Retries exhausted, re-raise
                    time.sleep(1)  # Wait 1 second before retrying

        logger.info(f"Clicking final export button for draft: '{draft_name}'")
        # Click the export confirm button
        export_btn = self.app.TextControl(searchDepth=2, Compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True))
        if not export_btn.Exists(0):
            raise AutomationError("Export button not found in export window")
        export_btn.Click(simulateMove=False)
        time.sleep(5)

        # Wait for export to complete
        st = time.time()
        while True:
            # self.get_window()
            if self.app_status != "pre_export": continue

            # Look for the export success close button
            succeed_close_btn = self.app.TextControl(searchDepth=2, Compare=ControlFinder.desc_matcher("ExportSucceedCloseBtn"))
            if succeed_close_btn.Exists(0):
                self.export_progress["status"] = "finished"
                self.export_progress["percent"] = 100
                self.export_progress["message"] = "Export complete"
                self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
                succeed_close_btn.Click(simulateMove=False)
                break

            # Scan text controls for progress percentage
            try:
                text_controls = self.app.GetChildren()
                for control in text_controls:
                    progress_text = ""
                    # Check control name
                    if hasattr(control, "Name") and control.Name and "%" in control.Name:
                        progress_text = control.Name
                    # Check control description
                    elif hasattr(control, "GetPropertyValue"):
                        desc = control.GetPropertyValue(30159) if hasattr(control, "GetPropertyValue") else ""
                        if desc and isinstance(desc, str) and "%" in desc:
                            progress_text = desc

                    if progress_text:
                        # Extract percentage (supports decimals)
                        percent_match = re.search(r'(\d+\.?\d*)%', progress_text)
                        print("progress_text is " + progress_text)
                        print("percent_match is ", percent_match)
                        if percent_match:
                            percent = float(percent_match.group(1))
                            print("percent is ", percent)
                            self.export_progress["percent"] = percent * 0.8 + 20
                            self.export_progress["message"] = "Exporting"
                            self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
                        break
            except Exception as e:
                self.export_progress["message"] = f"Error reading progress: {e}"
                self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]

            if time.time() - st > timeout:
                self.export_progress["status"] = "error"
                self.export_progress["message"] = f"Export timed out after {timeout} seconds"
                self.export_progress["elapsed"] = time.time() - self.export_progress["start_time"]
                raise AutomationError("Export timed out after %d seconds" % timeout)

            time.sleep(1)
        time.sleep(2)

        # Move exported file to target path
        if output_path is not None:
            shutil.move(export_path, output_path)

        logger.info(f"Export of '{draft_name}' to '{output_path}' completed")

        # Return to home page
        logger.info("back to home page")
        try:
            self.get_window()
            self.switch_to_home()
        except Exception as e:
            logger.warning(f"Failed to return to home page: {str(e)}; killing process and restarting")
            ProcessController.kill_jianying()

            if not ProcessController.restart_jianying():
                logger.critical("Failed to restart JianYing application. Aborting.")
                raise Exception("Failed to restart JianYing application")

            time.sleep(2)  # Wait for process to start
            ProcessController.kill_jianying_detector()


    def switch_to_home(self) -> None:
        """Switch to the JianYing home page"""
        if self.app_status == "home":
            return
        if self.app_status != "edit":
            raise AutomationError("Can only switch to home from edit mode")
        close_btn = self.app.GroupControl(searchDepth=1, ClassName="TitleBarButton", foundIndex=3)
        close_btn.Click(simulateMove=False)
        time.sleep(2)
        self.get_window()

    def get_window(self) -> None:
        """Find the JianYing window and bring it to the foreground"""
        if hasattr(self, "app") and self.app.Exists(0):
            self.app.SetTopmost(False)

        self.app = uia.WindowControl(searchDepth=1, Compare=self.__jianying_window_cmp)
        if not self.app.Exists(0):
            raise AutomationError("JianYing window not found")

        # Look for a floating export window
        export_window = self.app.WindowControl(searchDepth=1, Name="导出")
        if export_window.Exists(0):
            self.app = export_window
            self.app_status = "pre_export"

        self.app.SetActive()
        self.app.SetTopmost()

    def __jianying_window_cmp(self, control: uia.WindowControl, depth: int) -> bool:
        if control.Name != "剪映专业版":
            return False
        if "HomePage".lower() in control.ClassName.lower():
            self.app_status = "home"
            return True
        if "MainWindow".lower() in control.ClassName.lower():
            self.app_status = "edit"
            return True
        return False
