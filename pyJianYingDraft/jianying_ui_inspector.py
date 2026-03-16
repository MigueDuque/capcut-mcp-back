import uiautomation as auto
import time
import json
from typing import Dict, List, Optional

class JianYingUIInspector:
    def __init__(self):
        self.jianying_window = None

    def find_jianying_window(self) -> bool:
        """Find the JianYing window"""
        # Try multiple possible window names
        window_names = [
            "剪映",
            "JianYing",
            "CapCut",
            "剪映专业版"
        ]

        for name in window_names:
            try:
                # Search by window title
                window = auto.WindowControl(searchDepth=1, Name=name)
                if window.Exists(0, 0):
                    self.jianying_window = window
                    print(f"JianYing window found: {name}")
                    return True

                # Search by class name (if known)
                window = auto.WindowControl(searchDepth=1, ClassName="Qt5QWindowIcon")
                if window.Exists(0, 0) and name.lower() in window.Name.lower():
                    self.jianying_window = window
                    print(f"JianYing window found: {window.Name}")
                    return True
            except Exception as e:
                continue

        # If not found by name, enumerate all windows
        print("Not found by name; enumerating all windows...")
        for window in auto.GetRootControl().GetChildren():
            if window.ControlType == auto.ControlType.WindowControl:
                window_title = window.Name
                if any(keyword in window_title for keyword in ["剪映", "JianYing", "CapCut"]):
                    self.jianying_window = window
                    print(f"JianYing window found: {window_title}")
                    return True

        print("JianYing window not found; make sure JianYing is running")
        return False

    def get_control_info(self, control) -> Dict:
        """Get detailed information about a control"""
        try:
            info = {
                "Name": control.Name,
                "ControlType": control.ControlTypeName,
                "ClassName": getattr(control, 'ClassName', ''),
                "AutomationId": getattr(control, 'AutomationId', ''),
                "BoundingRectangle": {
                    "left": control.BoundingRectangle.left,
                    "top": control.BoundingRectangle.top,
                    "right": control.BoundingRectangle.right,
                    "bottom": control.BoundingRectangle.bottom,
                    "width": control.BoundingRectangle.width(),
                    "height": control.BoundingRectangle.height()
                },
                "IsEnabled": control.IsEnabled,
                "IsVisible": getattr(control, 'IsOffscreen', True) == False,
                "ProcessId": getattr(control, 'ProcessId', 0)
            }

            # Get the FullDescription property (property ID: 30159)
            try:
                if hasattr(control, 'GetCurrentPropertyValue'):
                    full_description = control.GetCurrentPropertyValue(30159)
                    info["FullDescription"] = full_description or ""
                else:
                    info["FullDescription"] = ""
            except Exception as e:
                info["FullDescription"] = ""
                info["FullDescriptionError"] = str(e)

            # Retrieve text content via multiple methods
            text_content = ""

            # Method 1: via Value pattern
            try:
                if hasattr(control, 'GetValuePattern'):
                    value_pattern = control.GetValuePattern()
                    if value_pattern:
                        text_content = value_pattern.Value
            except:
                pass

            # Method 2: via Text pattern
            try:
                if hasattr(control, 'GetTextPattern'):
                    text_pattern = control.GetTextPattern()
                    if text_pattern:
                        text_content = text_pattern.DocumentRange.GetText(-1)
            except:
                pass

            # Method 3: via direct property access
            try:
                if not text_content and hasattr(control, 'CurrentValue'):
                    text_content = str(control.CurrentValue)
            except:
                pass

            # Method 4: via LegacyIAccessible pattern
            try:
                if not text_content and hasattr(control, 'GetLegacyIAccessiblePattern'):
                    legacy_pattern = control.GetLegacyIAccessiblePattern()
                    if legacy_pattern:
                        text_content = legacy_pattern.CurrentValue or legacy_pattern.CurrentName
            except:
                pass

            # Method 5: for QML controls, try control-specific property
            try:
                if not text_content and "QQuickText" in info["ClassName"]:
                    # QML Text controls may require special handling
                    if hasattr(control, 'GetCurrentPropertyValue'):
                        # Try to read the Text property
                        text_content = control.GetCurrentPropertyValue(auto.PropertyId.ValueValueProperty)
            except:
                pass

            info["TextContent"] = text_content or ""
            info["HasText"] = bool(text_content)

            # Retrieve remaining properties
            try:
                info["Value"] = control.GetValuePattern().Value if hasattr(control, 'GetValuePattern') else ""
            except:
                info["Value"] = ""

            try:
                info["IsSelected"] = control.GetSelectionItemPattern().IsSelected if hasattr(control, 'GetSelectionItemPattern') else False
            except:
                info["IsSelected"] = False

            return info
        except Exception as e:
            return {"Error": str(e), "Name": "failed to retrieve info"}

    def build_ui_tree(self, control, max_depth: int = 10, current_depth: int = 0) -> Dict:
        """Recursively build the UI element tree"""
        if current_depth >= max_depth:
            return {"MaxDepthReached": True}

        node = self.get_control_info(control)
        node["Depth"] = current_depth
        node["Children"] = []

        try:
            children = control.GetChildren()
            for child in children:
                if child.Exists(0, 0):  # Skip non-existent children
                    child_node = self.build_ui_tree(child, max_depth, current_depth + 1)
                    node["Children"].append(child_node)
        except Exception as e:
            node["ChildrenError"] = str(e)

        return node

    def print_ui_tree(self, node: Dict, indent: str = ""):
        """Print the UI tree structure"""
        control_type = node.get("ControlType", "Unknown")
        name = node.get("Name", "")
        class_name = node.get("ClassName", "")
        automation_id = node.get("AutomationId", "")
        full_description = node.get("FullDescription", "")

        # Build display text
        display_parts = [control_type]
        if name:
            display_parts.append(f'Name="{name}"')
        if class_name:
            display_parts.append(f'Class="{class_name}"')
        if automation_id:
            display_parts.append(f'Id="{automation_id}"')
        if full_description:
            # Truncate FullDescription to avoid overly long output
            desc_display = full_description[:100] + "..." if len(full_description) > 100 else full_description
            display_parts.append(f'FullDesc="{desc_display}"')

        display_text = " ".join(display_parts)

        # Append position info
        if "BoundingRectangle" in node:
            rect = node["BoundingRectangle"]
            display_text += f" [{rect['left']},{rect['top']},{rect['width']}x{rect['height']}]"

        print(f"{indent}{display_text}")

        # Recursively print children
        for child in node.get("Children", []):
            self.print_ui_tree(child, indent + "  ")

    def save_ui_tree_to_file(self, tree: Dict, filename: str = "jianying_ui_tree.json"):
        """Save the UI tree to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(tree, f, ensure_ascii=False, indent=2)
            print(f"UI tree saved to: {filename}")
        except Exception as e:
            print(f"Failed to save file: {e}")

    def find_elements_by_type(self, tree: Dict, control_type: str) -> List[Dict]:
        """Find elements by control type"""
        results = []

        if tree.get("ControlType") == control_type:
            results.append(tree)

        for child in tree.get("Children", []):
            results.extend(self.find_elements_by_type(child, control_type))

        return results

    def find_elements_by_name(self, tree: Dict, name: str) -> List[Dict]:
        """Find elements by name"""
        results = []

        if name.lower() in tree.get("Name", "").lower():
            results.append(tree)

        for child in tree.get("Children", []):
            results.extend(self.find_elements_by_name(child, name))

        return results

    def find_text_controls(self, tree: Dict) -> List[Dict]:
        """Find all controls that contain text"""
        results = []

        if tree.get("HasText") and tree.get("TextContent"):
            results.append({
                "ControlType": tree.get("ControlType"),
                "Name": tree.get("Name"),
                "ClassName": tree.get("ClassName"),
                "TextContent": tree.get("TextContent"),
                "BoundingRectangle": tree.get("BoundingRectangle")
            })

        for child in tree.get("Children", []):
            results.extend(self.find_text_controls(child))

        return results

    def inspect_jianying_ui(self, max_depth: int = 8, save_to_file: bool = True):
        """Inspect the JianYing UI and display the element tree"""
        print("Searching for JianYing window...")

        if not self.find_jianying_window():
            return None

        print(f"Window: {self.jianying_window.Name}")
        print(f"Bounds: {self.jianying_window.BoundingRectangle}")
        print("\nBuilding UI element tree...")

        # Build UI tree
        ui_tree = self.build_ui_tree(self.jianying_window, max_depth)

        print("\n=== JianYing UI Element Tree ===")
        self.print_ui_tree(ui_tree)

        if save_to_file:
            self.save_ui_tree_to_file(ui_tree)

        return ui_tree

    def list_all_windows(self):
        """List all windows (useful for debugging)"""
        print("All current windows:")
        for window in auto.GetRootControl().GetChildren():
            if window.ControlType == auto.ControlType.WindowControl:
                try:
                    print(f"- {window.Name} (PID: {getattr(window, 'ProcessId', 'Unknown')})")
                except:
                    print(f"- Unable to retrieve window info")

def main():
    """Entry point"""
    inspector = JianYingUIInspector()

    # If JianYing window is not found, list all windows for debugging
    if not inspector.find_jianying_window():
        print("\nListing all windows for reference:")
        inspector.list_all_windows()
        return

    # Inspect UI
    ui_tree = inspector.inspect_jianying_ui(max_depth=6, save_to_file=True)

    if ui_tree:
        # Example: find all button controls
        buttons = inspector.find_elements_by_type(ui_tree, "ButtonControl")
        print(f"\nFound {len(buttons)} button controls")

        # Example: find elements containing "导出"
        export_elements = inspector.find_elements_by_name(ui_tree, "导出")
        if export_elements:
            print(f"\nFound {len(export_elements)} element(s) containing '导出':")
            for elem in export_elements:
                print(f"  - {elem.get('ControlType')}: {elem.get('Name')}")

        # Also: find all controls with text content
        text_controls = inspector.find_text_controls(ui_tree)
        if text_controls:
            print(f"\nFound {len(text_controls)} control(s) with text content:")
            for ctrl in text_controls:
                print(f"  - {ctrl['ControlType']}: '{ctrl['TextContent']}'")

if __name__ == "__main__":
    main()
