
import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="scanivalve",
    py_modules=['scanivalve','scanigui'],
    version="0.1",
    author = "Paulo Jabardo",
    author_email = "pjabardo@gmail.com",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/tunelipt/scanivalve",
    packages = setuptools.find_packages(),
    classifiers = ["Programming Language :: Python :: 3",
                   "License :: OSI Approved :: MIT License",
                   "Operating System :: OS Independent"],
    python_requires='>=3.4')

    
    
