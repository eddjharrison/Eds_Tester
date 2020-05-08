from qgis.core import *
import os
import shutil
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsCoordinateReferenceSystem
import processing
from qgis import *


class AnalyseDTM():

    def __init__(self):

        # INPUTS
        self.DTM = (
            '/Users/eh/Emerald Geo/Developments - Documents/DeveloperWorkspaces/EH/QGis/Projects/Image_Export/E18_Nye_Veier/Øst_LR_DTM10.tif')
        self.output_basename = ('LR_' + '_')
        self.output_path = ('/Users/EH/Emerald Geo/Developments - Documents/DeveloperWorkspaces/EH/QGis/')
        self.output_folder = os.path.join(self.output_path, self.output_basename)
        self.temp = ('/Users/EH/Emerald Geo/Developments - Documents/DeveloperWorkspaces/EH/QGis/LRtemp.tif')

        self.min_height = '3'
        self.QgsCoord = 'QgsCoordinateReferenceSystem'
        self.CRS = str("('EPSG:25832')")
        self.output_CRS = (self.QgsCoord + self.CRS)
        print(self.output_CRS)

        # OUTPUTS
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
        else:
            shutil.rmtree(self.output_folder)
            os.makedirs(self.output_folder)

        translated = self.TranslateRaster()
        slope = self.SlopeToPolygons(translated)
        a = self.ClipRasterandExportdata(translated, slope)

    def TranslateRaster(self):

        # Sets anything below 0 as NO DATA
        # This removes anonomously high slopes on TIF borders where it goes from no data to high elevations
        # self.DTM = iface.activeLayer()

        #        translateFeatures = processing.runAndLoadResults("gdal:translate", {
        #        'INPUT':self.DTM,
        #        'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:25833'),
        #        'NODATA':0,
        #        'COPY_SUBDATASETS':False,
        #        'OPTIONS':'',
        #        'EXTRA':'',
        #        'DATA_TYPE':0,
        #        'OUTPUT': 'TEMPORARY_OUTPUT'})

        t = processing.run("gdal:translate", {
            'INPUT': self.DTM,
            'TARGET_CRS': None,
            'NODATA': 0,
            'COPY_SUBDATASETS': False,
            'OPTIONS': '',
            'EXTRA': '',
            'DATA_TYPE': 0,
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        #        fillnodata = processing.run("gdal:fillnodata", {
        #        'INPUT': self.DTM,
        #        'BAND':1,
        #        'DISTANCE':10,
        #        'ITERATIONS':0,
        #        'NO_MASK':False,
        #        'MASK_LAYER':None,
        #        'OPTIONS':'',
        #        'EXTRA':'',
        #        'OUTPUT':'TEMPORARY_OUTPUT'})

        #        RemoveSub0values = processing.run("qgis:rastercalculator", {
        #        'EXPRESSION':'((\"OUTPUT@1\">0)*\"OUTPUT@1\") / ((\"OUTPUT@1\">0)*1 + (\"OUTPUT@1\"<=0)*0)',
        #        'LAYERS': translateFeatures['OUTPUT'],
        #        'CELLSIZE':None,
        #        'EXTENT':None,
        #        'CRS': QgsCoordinateReferenceSystem('EPSG:25833'),
        #        'OUTPUT': 'TEMPORARY_OUTPUT' })

        trans = t['OUTPUT']
        return trans

    def SlopeToPolygons(self, trans):
        Shapes = os.path.join(self.output_folder, self.output_basename + 'bedRockPolygons.shp')

        # Calculate the slope values for each pixel
        Slope = processing.runAndLoadResults("native:slope", {
            'INPUT': trans,
            'Z_FACTOR': 1,
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        slope1 = Slope['OUTPUT']
        print(slope1)

        # Sets anything with a slope less than 45 degrees as NO DATA
        calculatedOver45deg = processing.runAndLoadResults("qgis:rastercalculator", {
            'EXPRESSION': '((\"OUTPUT@1\">45)*\"OUTPUT@1\") / ((\"OUTPUT@1\">45)*1 + (\"OUTPUT@1\"<=45)*0)',
            # ((\"@1\">45)*\"@1\") / ((\"@1\">45)*1 + (\"@1\"<=45)*0)
            # \"DTM_Polygon_temp@1\"  >= 45  ) * \"DTM_Polygon_temp@1\"
            'LAYERS': slope1,
            'CELLSIZE': None,
            'EXTENT': None,
            'CRS': QgsCoordinateReferenceSystem('EPSG:25833'),
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        # This creates the Polygons
        Poly = processing.run("native:pixelstopolygons", {
            'INPUT_RASTER': calculatedOver45deg['OUTPUT'],
            'RASTER_BAND': 1,
            'FIELD_NAME': 'VALUE',
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        dissolve = processing.run("native:dissolve", {
            'INPUT': Poly['OUTPUT'],
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        multiToSingle = processing.run("native:multiparttosingleparts", {
            'INPUT': dissolve['OUTPUT'],
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        calculate_elevation_range = processing.run("native:zonalstatistics", {
            'INPUT_RASTER': trans,
            'RASTER_BAND': 1,
            'INPUT_VECTOR': multiToSingle['OUTPUT'],
            'COLUMN_PREFIX': '_',
            'STATISTICS': [7]})

        extractRange_overX = processing.runAndLoadResults("native:extractbyattribute", {
            'INPUT': multiToSingle['OUTPUT'],
            'FIELD': '_range',
            'OPERATOR': 2,
            'VALUE': '3',
            'CRS': QgsCoordinateReferenceSystem('EPSG:25833'),
            'OUTPUT': Shapes})

        #        assCRS = processing.run("native:assignprojection", {
        #        'INPUT': PolyShapefile['OUTPUT'],
        #        'CRS': self.output_CRS,
        #        'OUTPUT': Shapes})

        Shapefile = extractRange_overX['OUTPUT']

        return Shapefile

    #
    def ClipRasterandExportdata(self, trans, Shapefile):

        PointShape = os.path.join(self.output_folder, self.output_basename + 'bedrockPoint.shp')
        PointShapeCSV = os.path.join(self.output_folder, self.output_basename + 'bedrockPoint_.csv')

        clip_raster = processing.run("saga:cliprasterwithpolygon", {
            'INPUT': trans,
            'POLYGONS': Shapefile,
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        create_points = processing.run("native:pixelstopoints", {
            'INPUT_RASTER': clip_raster['OUTPUT'],
            'RASTER_BAND': 1,
            'FIELD_NAME': 'VALUE',
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        #        assCRS = processing.run("native:assignprojection", {
        #        'INPUT': create_points['OUTPUT'],
        #        'CRS': self.output_CRS,
        #        'OUTPUT':'TEMPORARY_OUTPUT'})

        addXY = processing.run("native:addxyfields", {
            'INPUT': create_points['OUTPUT'],
            'CRS': self.output_CRS,
            'PREFIX': '',
            'OUTPUT': PointShape})

        VectorPoints = addXY['OUTPUT']

        addOutcropID = processing.run("qgis:fieldcalculator", {
            'INPUT': VectorPoints,
            'FIELD_NAME': 'Outcrop ID',
            'FIELD_TYPE': 2,
            'FIELD_LENGTH': 80,
            'FIELD_PRECISION': 3,
            'NEW_FIELD': True,
            'FORMULA': '\'Outcropping_Bedrock\'',
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        bedConf = processing.run("qgis:fieldcalculator", {
            'INPUT': addOutcropID['OUTPUT'],
            'FIELD_NAME': 'bedConf',
            'FIELD_TYPE': 0,
            'FIELD_LENGTH': 80,
            'FIELD_PRECISION': 3,
            'NEW_FIELD': True,
            'FORMULA': '0',
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        ColourCode = processing.run("qgis:fieldcalculator", {
            'INPUT': bedConf['OUTPUT'],
            'FIELD_NAME': 'ColourCode',
            'FIELD_TYPE': 0,
            'FIELD_LENGTH': 80,
            'FIELD_PRECISION': 3,
            'NEW_FIELD': True,
            'FORMULA': '1',
            'OUTPUT': 'TEMPORARY_OUTPUT'})

        refactorOutcrops = processing.run("qgis:refactorfields", {
            'INPUT': ColourCode['OUTPUT'],
            'FIELDS_MAPPING': [
                {'expression': '"Outcrop ID"', 'length': 80, 'name': 'Outcrop ID', 'precision': 3, 'type': 10},
                {'expression': '"x"', 'length': 20, 'name': 'X', 'precision': 10, 'type': 6},
                {'expression': '"y"', 'length': 20, 'name': 'Y', 'precision': 10, 'type': 6},
                {'expression': '"VALUE"', 'length': 20, 'name': 'Z', 'precision': 8, 'type': 6},
                {'expression': '"bedConf"', 'length': 10, 'name': 'bedConf', 'precision': 3, 'type': 2},
                {'expression': '"ColourCode"', 'length': 10, 'name': 'ColourCode', 'precision': 3, 'type': 2}],
            'CRS': self.output_path,
            'OUTPUT': PointShapeCSV})


#
obj = AnalyseDTM()
