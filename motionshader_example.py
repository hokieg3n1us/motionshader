import multiprocessing as mp
from datetime import datetime, timedelta

import dask.dataframe
import requests

import motionshader

if __name__ == '__main__':
    # Motionshader expects a time indexed, sorted, Dask DataFrame with columns containing EPSG:4326 coordinates.
    # Motionshader is opinionated about using Dask DataFrames, for scaling this process to big data.
    df = dask.dataframe.read_csv('NYC.csv', usecols=['timestamp', 'longitude', 'latitude'])
    df['timestamp'] = dask.dataframe.to_datetime(df['timestamp'])
    df = df.set_index('timestamp', npartitions=mp.cpu_count(), compute=True).persist()

    # Define a Basemap using a WMS Service and associated layer. Assumes EPSG:4326.
    # Provide a requests.Session() that can be customized for authentication or 2-way SSL verification.
    basemap = motionshader.Basemap(requests.Session(), 'https://basemap.nationalmap.gov/arcgis/services/USGSImageryOnly/MapServer/WMSServer', '0')

    # Define the Dataset, providing a Dask DataFrame and the names of the longitude and latitude columns.
    dataset = motionshader.Dataset(df, 'longitude', 'latitude')

    # Define the MotionVideo, providing the dataset to be rendered and the basemap service.
    motion_video = motionshader.MotionVideo(dataset, basemap)

    # GeospatialViewport allows defining where the 'camera' looks on the globe, and the resolution of the output.
    # TemporalPlayback defines the temporal bounds, temporal size of a frame, and the frames per second for the output.
    # In this example, a single frame contains 30 minutes of data, and steps forward 15 minutes between frames.
    viewport = motionshader.GeospatialViewport(-74.25909, -73.700181, 40.477399, 40.916178, 1920, 1080)
    playback = motionshader.TemporalPlayback(datetime(2020, 4, 1), datetime(2020, 4, 2), timedelta(minutes=30),
                                             timedelta(minutes=15), 5)

    # MotionVideo can be output as either a GIF or an MP4.
    motion_video.to_gif(viewport, playback, 'NYC')
    motion_video.to_video(viewport, playback, 'NYC')
