import setuptools

from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setuptools.setup(
    name="motionshader",
    version="1.0.5",
    author="Barry Bragg",
    author_email="hokieg3n1us@gmail.com",
    description="Generate a gif or mp4 from geospatial vector data.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/hokieg3n1us/motionshader",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=['motionshader'],
    python_requires=">=3.6",
    install_requires=['datashader', 'imageio', 'imageio-ffmpeg']
)
