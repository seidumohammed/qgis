from .basemap_manager import BasemapManager

def classFactory(iface):
    return BasemapManager(iface)