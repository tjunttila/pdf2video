import setuptools

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="pdf2video", # Replace with your own username
    version="0.2.1",
    author="T. Junttila",
    author_email="Tommi.Junttila@aalto.fi",
    description="A tool for making narrated videos from PDF presentations.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tjunttila/pdf2video",
    packages=setuptools.find_packages(),
    license = "MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    setup_requires=['wheel']
)
