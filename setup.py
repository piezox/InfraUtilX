from setuptools import setup, find_packages

setup(
    name="infrautilx",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pulumi>=3.0.0",
        "pulumi-aws>=6.0.0",
        "boto3>=1.26.0",
    ],
    python_requires=">=3.8",
    author="Stefano Marzani",  # TODO: Replace with your name
    author_email="stefano@piezo.cc",  # TODO: Replace with your email
    description="A reusable AWS infrastructure library built with Pulumi",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/piezox/InfraUtilX",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 