from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Define dependencies manually for setup.py compatibility
requirements = [
    "numpy<2.0.0",
    "torch>=2.0.0",
    "torchaudio>=2.2.0",
    "PySimpleGUI>=4.60.0",
    "python-dotenv>=0.19.0",
    # For Demucs, we'll need to install it separately with pip
    # as setup.py doesn't handle git URLs well
]

setup(
    name="open-karaoke",
    version="0.1.0",
    author="Spencer Frost",
    author_email="s.s.frost@gmail.com",
    description="A desktop application for creating karaoke tracks by separating vocals from music",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/spencerfrost/open-karaoke",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "open-karaoke=main:main",
        ],
    },
)
