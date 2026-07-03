// Define Switzerland's bounding box
var switzerland = ee.Geometry.Rectangle([5.9561, 45.8179, 10.4911, 47.8084]);

// Load Landsat 8 image collection
var landsat = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
               .filterBounds(switzerland)
               .filterDate('2021-01-01', '2023-12-31')
               .filter(ee.Filter.lt('CLOUD_COVER', 10));

// Constants for Band 10
var K1 = 774.89;
var K2 = 1321.08;
var LAMBDA = 10.9;
var RHO = 1.438e-2;

// Calculate LST
var calculateLST = function(image) {
  var radiance = image.select('ST_B10').multiply(0.00341802).add(149);
  var brightnessTemp = radiance.multiply(K2).divide(radiance.add(K1)).subtract(273.15);
  var ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']);
  var emissivity = ndvi.expression('0.004 * NDVI + 0.986', {'NDVI': ndvi});
  var lst = brightnessTemp.divide(
    ee.Image(1).add(emissivity.multiply(LAMBDA).multiply(brightnessTemp.divide(RHO)).log())
  );
  return lst.rename('LST').set('system:time_start', image.get('system:time_start'));
};

var lstCollection = landsat.map(calculateLST);
var minLST = lstCollection.min();
var maxLST = lstCollection.max();
var extremeHeatChange = maxLST.subtract(minLST).clip(switzerland);

// Export to Drive
Export.image.toDrive({
  image: extremeHeatChange,
  description: 'LTLST_Switzerland',
  folder: 'GEE_exports',
  scale: 30,
  region: switzerland,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});   
