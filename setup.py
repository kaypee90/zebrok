from setuptools import setup

setup(
    name="Zebrok",
    url="https://github.com/kaypee90/zebrok",
    author="kaypee90",
    author_email="kaypee90@yahoo.com",
    packages=["zebrok"],
    install_requires=["pyzmq==26.0.2"],
    version="0.0.1",
    license="MIT",
    description="Brokerless task queue",
    long_description=open("README.md").read(),
)
