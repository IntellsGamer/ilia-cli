from setuptools import setup, find_packages

setup(
    name="{{ project_name }}",
    version="{{ version }}",
    description="{{ description }}",
    author="{{ author }}",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "{{ project_name }}=cli:main",
        ],
    },
)
