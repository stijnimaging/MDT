#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
from mdt.cli_scripts.mdt_gui import GUI

__author__ = 'Robbert Harms'
__date__ = "2015-08-18"
__maintainer__ = "Robbert Harms"
__email__ = "robbert.harms@maastrichtuniversity.nl"


"""A shortcut for mdt_gui"""


class GUI_Shortcut(GUI):
    pass


if __name__ == '__main__':
    GUI_Shortcut().start()