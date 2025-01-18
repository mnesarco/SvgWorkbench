# SPDX-License: LGPL-3.0-or-later
# (c) 2025 Frank David Martínez Muñoz. <mnesarco at gmail.com>

from .vendor.fcapi.resources import Resources
from .vendor.fcapi.commands import CommandRegistry

from . import resources as svgwb_resources
from .preferences import SvgImportPreferences, SvgExportPreferences

resources = Resources(svgwb_resources)
commands = CommandRegistry("SvgWB_")
import_pref = SvgImportPreferences()
export_pref = SvgExportPreferences()
