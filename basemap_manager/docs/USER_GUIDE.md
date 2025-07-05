# Basemap Manager - User Guide

## Installation
1. Download the plugin ZIP file
2. In QGIS, go to `Plugins > Manage and Install Plugins > Install from ZIP`
3. Select the downloaded ZIP file
4. Restart QGIS

## Basic Usage
1. Click the **Basemap Manager** toolbar icon 
2. Select a basemap from the list
3. Click "Apply Basemap" or double-click the basemap name

![Interface](screenshot.png)

## Features
### Basemap Categories
- **Standard**: OSM-based maps
- **Satellite**: Aerial imagery
- **Dark**: Dark-themed basemaps
- **Thematic**: Specialized maps
- **Custom**: User-added basemaps

### Search Functionality
Type in the search box to filter basemaps by name

### Layer Management
- Previous basemap automatically removed (configurable)
- New basemap added to bottom of layer stack
- Automatic CRS correction (EPSG:3857)

## Custom Basemaps
1. Go to the **Settings** tab
2. Click **Add New**
3. Enter provider details:
   - Name: Display name
   - URL: XYZ template with `{x}`, `{y}`, `{z}` placeholders
   - Max Zoom (optional)
4. Click **Save**

## Troubleshooting
| Issue | Solution |
|-------|----------|
| Basemap not loading | Check internet connection |
| "Invalid Layer" error | Verify URL template format |
| Projection mismatch | Enable "Auto-set CRS" in Settings |
| Basemap doesn't appear | Check layer panel visibility |

## Contact Support
Email: seidumohammed64@gmail.com  
GitHub: [github.com/basemap-manager](https://github.com/seidumohammed/qgis/tree/main/basemap_manager)