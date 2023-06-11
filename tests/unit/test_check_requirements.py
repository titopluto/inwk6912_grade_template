import os
from unittest import TestCase

from tests.unit import BASE_DIR

LAB_CONFIG_FOLDER = "lab/configs"
CONFIG_FILES = ['R11.cfg',
                'R12.cfg',
                'R21.cfg',
                'R22.cfg',
                'R23.cfg']


class TestLabFolder(TestCase):
    def test_lab_folder_exists(self):
        folder_path = os.path.join(BASE_DIR, LAB_CONFIG_FOLDER)
        self.assertTrue(os.path.isdir(folder_path), f"Folder '{folder_path}' does not exist.")

    def test_lab_files_exist(self):
        folder_path = os.path.join(BASE_DIR, LAB_CONFIG_FOLDER)

        for file in CONFIG_FILES:
            file_path = os.path.join(folder_path, file)
            self.assertTrue(os.path.isfile(file_path), f"File '{file_path}' does not exist.")

