import re
from pathlib import Path

from setuptools import setup

HERE = Path(__file__).parent
VERSION = re.search(
    r'^__version__ = "([^"]+)"',
    (HERE / "zebrok" / "__init__.py").read_text(encoding="utf-8"),
    re.MULTILINE,
).group(1)

setup(
    name="Zebrok",
    url="https://github.com/kaypee90/zebrok",
    author="kaypee90",
    author_email="kaypee90@yahoo.com",
    packages=["zebrok"],
    install_requires=["pyzmq==27.1.0"],
    python_requires=">=3.10",
    version=VERSION,
    license="MIT",
    description="Brokerless task queue",
    long_description=(HERE / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
)
