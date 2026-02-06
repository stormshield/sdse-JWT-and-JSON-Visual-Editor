#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Plugin utilities for resource path resolution
Compatible with both development and PyInstaller bundled environments
"""

import os
import sys

def get_plugin_resource_path(plugin_folder_path, relative_path):
    """
    Get absolute path to plugin resource, works for dev and for PyInstaller.
    
    Args:
        plugin_folder_path: The relative path from plugins/ to the plugin folder
                           Example: "SDS plugins/policySign" or "Required plugins/certificates"
        relative_path: The relative path to the resource within the plugin folder
                      Example: "languages.json"
    
    Returns:
        Absolute path to the resource
    
    Example:
        path = get_plugin_resource_path("SDS plugins/policySign", "languages.json")
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # In PyInstaller, plugins are in _MEIPASS/plugins/...
        plugin_rel = os.path.join("plugins", plugin_folder_path, relative_path)
        return os.path.join(base_path, plugin_rel)
    except Exception:
        # In development, we need to find the actual plugin directory
        # This function is typically imported by a plugin, so we can't use __file__
        # Instead, we'll construct from the main script location
        try:
            main_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        except:
            main_dir = os.getcwd()
        
        return os.path.join(main_dir, "plugins", plugin_folder_path, relative_path)
