#------------------------------------------------------------------------------
#  Copyright (c) 2012, Enthought, Inc.
#  All rights reserved.
#------------------------------------------------------------------------------
import unittest, os
from uuid import uuid4

from enaml.qt.qt.QtGui import QApplication, QFileDialog
from enaml.qt.qt_file_dialog import QtFileDialog
from enaml.qt.qt_local_pipe import QtLocalPipe

class TestQtFileDialog(unittest.TestCase):
    """ Unit tests for the QtFileDialog
    
    """
    def setUp(self):
        """ Set up the widget for testing

        """
        self.file_dialog = QtFileDialog(None, uuid4().hex, QtLocalPipe(),
                                        QtLocalPipe())
        self.file_dialog.create()

    def test_set_mode(self):
        """ Test the QtFileDialog's set_mode command

        """
        self.file_dialog.recv('set_mode', {'value':'open'})
        mode = self.file_dialog.widget.acceptMode()
        self.assertEqual(mode, QFileDialog.AcceptOpen)

    def test_set_multi_select(self):
        """ Test the QtFileDialog's set_multi_select command

        """
        self.file_dialog.recv('set_multi_select', {'value':True})
        multi = self.file_dialog.widget.fileMode()
        self.assertEqual(multi, QFileDialog.ExistingFiles)

    def test_set_directory(self):
        """ Test the QtFileDialog's set_directory command

        """
        # The directory must exist for this command to work properly,
        # so we use the current directory
        dir_path = os.path.abspath(os.path.curdir)
        self.file_dialog.recv('set_directory', {'value':dir_path})
        widget_path = self.file_dialog.widget.directory().absolutePath()
        self.assertEqual(widget_path, dir_path)

    def test_set_filename(self):
        """ Test the QtFileDialog's set_filename command

        """
        # The filename must exist for this command to work properly,
        # so we use this file
        file_path = os.path.abspath(__file__)
        self.file_dialog.recv('set_filename', {'value':file_path})
        widget_file_path = self.file_dialog.widget.selectedFiles()[0]
        self.assertEqual(widget_file_path, file_path)

    def test_set_filters(self):
        """ Test the QtFileDialog's set_filters command

        """
        filters = ['Python files (.py)']
        self.file_dialog.recv('set_filters', {'value':filters})
        widget_filters = self.file_dialog.widget.nameFilters()
        self.assertEqual(widget_filters, filters)

    # XXX Test file dialog events?

if __name__ == '__main__':
    app = QApplication([])
    unittest.main()
