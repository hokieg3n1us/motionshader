import setuptools

setuptools.setup(
    name="motionshader",
    version="1.0.3",
    author="Barry Bragg",
    author_email="hokieg3n1us@gmail.com",
    description="Generate a gif or mp4 from geospatial vector data.",
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
