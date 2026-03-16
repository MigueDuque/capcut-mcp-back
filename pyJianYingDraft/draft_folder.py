"""Draft folder manager"""

import os
import shutil

from typing import List

from .script_file import Script_file


class Draft_folder:
    """Manages a folder containing one or more CapCut drafts"""

    folder_path: str
    """Root path of the folder"""

    def __init__(self, folder_path: str):
        """Initialize the draft folder manager.

        Args:
            folder_path (`str`): Folder containing draft sub-directories.
                Typically the path where CapCut/JianYing saves its drafts.

        Raises:
            `FileNotFoundError`: The path does not exist.
        """
        self.folder_path = folder_path

        if not os.path.exists(self.folder_path):
            raise FileNotFoundError(f"Root folder '{self.folder_path}' does not exist")

    def list_drafts(self) -> List[str]:
        """List the names of all draft sub-folders.

        Note: this simply lists sub-folder names; it does not validate their format.
        """
        return [f for f in os.listdir(self.folder_path) if os.path.isdir(os.path.join(self.folder_path, f))]

    def remove(self, draft_name: str) -> None:
        """Delete the draft with the given name.

        Args:
            draft_name (`str`): Draft name (i.e. the sub-folder name).

        Raises:
            `FileNotFoundError`: The draft does not exist.
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"Draft folder '{draft_name}' does not exist")

        shutil.rmtree(draft_path)

    def inspect_material(self, draft_name: str) -> None:
        """Print the sticker/bubble/text-effect metadata for the given draft.

        Args:
            draft_name (`str`): Draft name (i.e. the sub-folder name).

        Raises:
            `FileNotFoundError`: The draft does not exist.
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"Draft folder '{draft_name}' does not exist")

        script_file = self.load_template(draft_name)
        script_file.inspect_material()

    def load_template(self, draft_name: str) -> Script_file:
        """Open an existing draft as a template for editing.

        Args:
            draft_name (`str`): Draft name (i.e. the sub-folder name).

        Returns:
            `Script_file`: The draft opened in template mode.

        Raises:
            `FileNotFoundError`: The draft does not exist.
        """
        draft_path = os.path.join(self.folder_path, draft_name)
        if not os.path.exists(draft_path):
            raise FileNotFoundError(f"Draft folder '{draft_name}' does not exist")

        return Script_file.load_template(os.path.join(draft_path, "draft_info.json"))

    def duplicate_as_template(self, template_name: str, new_draft_name: str, allow_replace: bool = False) -> Script_file:
        """Copy an existing draft and open the copy for editing.

        Args:
            template_name (`str`): Name of the source draft.
            new_draft_name (`str`): Name for the new (copied) draft.
            allow_replace (`bool`, optional): Whether to overwrite an existing draft with the same name. Defaults to False.

        Returns:
            `Script_file`: The **copied** draft opened in template mode.

        Raises:
            `FileNotFoundError`: The source draft does not exist.
            `FileExistsError`: A draft named `new_draft_name` already exists and `allow_replace` is False.
        """
        template_path = os.path.join(self.folder_path, template_name)
        new_draft_path = os.path.join(self.folder_path, new_draft_name)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template draft '{template_name}' does not exist")
        if os.path.exists(new_draft_path) and not allow_replace:
            raise FileExistsError(f"Draft '{new_draft_name}' already exists and overwrite is not allowed")

        # Copy the draft folder
        shutil.copytree(template_path, new_draft_path, dirs_exist_ok=allow_replace)

        # Open the copy
        return self.load_template(new_draft_name)
