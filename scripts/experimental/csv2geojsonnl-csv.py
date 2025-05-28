
import pandas as pd
from shapely import wkt
import geojson
import sys, os,yaml, json
import logging, logging.handlers

# Function to convert WKT to GeoJSON feature
def wkt_to_geojson_feature(wkt_str, properties):
    geom = wkt.loads(wkt_str)
    return geojson.Feature(geometry=geom, properties=properties)

def main(path):
    # Load the CSV file
    csv_filename = "Neighborhoods KC.csv"
    df = pd.read_csv(os.path.join(path, csv_filename))
    df['name'] = df['name'].fillna('')
    df['description'] = df['description'].fillna(df['name'])

    # Create GeoJSON features
    features = []
    for idx, row in df.iterrows():
        properties = row.drop('WKT').to_dict()
        feature = wkt_to_geojson_feature(row['WKT'], properties)
        logger.debug(feature)
        features.append(feature)

    # Create a FeatureCollection
    feature_collection = geojson.FeatureCollection(features)
    logger.debug(json.dumps(feature_collection, indent=2))
    
    outfile_name = "output.geojson"
    # Save as GeoJSON
    with open(os.path.join(path, outfile_name), 'w') as f:
        geojson.dump(feature_collection, f)

    # Prepare data
    rows = []
    for feature in features:
        geometry = feature['geometry']
        properties = feature['properties']
        if geometry['type'] == 'Point':
            coordinates = geometry['coordinates']
            row = {
                'latitude': coordinates[1],
                'longitude': coordinates[0],
                **properties
            }
            rows.append(row)

    # Create DataFrame and save to CSV
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(path, 'geojson.csv'), index=False)

    print("GeoJSON file created successfully")

if __name__ == "__main__":

    logger = logging.getLogger()

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path")
        sys.exit(1)

    path = sys.argv[1]
    with open(os.path.join(path, "config.yaml"), "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    log_filename = os.path.join(path, "csv2geojson.log")

    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_filename, maxBytes=0, backupCount=5, encoding="utf-8"
    )
    if os.path.exists(log_filename) and os.path.getsize(log_filename) > 0:
        # Rotate the log file
        handler.doRollover()

    logger.addHandler(handler)

    sys.exit(main(path))