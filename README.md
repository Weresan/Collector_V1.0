# Collector V1.2 - Blender Add-on

**Author:** Were Sankofa  
**Blender Version:** 3.6+  
**Version:** 1.2  

---

## Overview

Collector is a Blender add-on designed to automatically organize cameras and lights into dedicated collections named `Cameras` and `Lights`. It also sequentially renames these objects for clean, professional organization.

---

## Features

- Automatically moves cameras and lights into their respective collections on file load and when new objects are added.
- Renames cameras and lights sequentially (e.g., `Camera 1`, `Camera 2`, `Light 1`, `Light 2`).
- Manual organization button in the sidebar panel.
- Toggle to enable/disable automatic organization.
- **New:** Export an organization report as a text file listing all cameras and lights and their collections.
- **New in 1.2:** Button to set the active camera from the selected camera and immediately switch the viewport to it.

---

## Usage

1. Enable the add-on in Blender's preferences.
2. In the 3D View Sidebar (press `N`), find the **Collector** panel.
3. Use the toggle to enable or disable automatic organization.
4. Click **Organize Cameras & Lights** to manually organize.
5. Click **Export Organization Report** to save a `.txt` file with the current organization status.

The report is saved in Blender's temporary directory, and the file path is displayed in the info bar.

---

## Installation

1. Download the `collector.py` script.
2. In Blender, go to *Edit > Preferences > Add-ons*.
3. Click *Install*, select the script, and enable it.

---

## Future Plans

Collector V2 aims to include customizable collection names, support for additional object types, smart cleanup, batch renaming, and integration with asset libraries.

---

## License

MIT License

---

## Contact

Created by Were Sankofa  
[(https://github.com/Weresan)]  
