<!-- Docs readme.md -->
# Docs Directory

Contains documentation and example images for the Swiss Crack project. See [root README](../README.md) for the full workflow.

## Subdirectories

- **images/**:
  - `road_buffering_example.png`: Road buffering with lane widths in QGIS.
  - `mask_filter_example.png`: Geometry filtering with external features.
  - `gradcam_results.png`: Guided Grad-CAM visualizations from `src/modeling/visualize_gradcam.py`.
  - `traffic_vs_crack_plot.png`: Traffic volume vs. RHCD plot from `src/visualization/plot_correlations.py`.
  - `lst_vs_crack_plot.png`: LT-LST-A vs. RHCD plot from `src/visualization/plot_correlations.py`.

# Long-Term Land Surface Temperature Anomalies (LT-LST-A)

Generate `data/processed/LTLST.gpkg` using Google Earth Engine (GEE) with Landsat 8 (2021–2023):

- Run the following script in GEE to export the result to Google Drive.
- Convert the exported file to data/processed/LTLST.gpkg using QGIS.

```javascript
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