from setuptools import setup, find_packages

setup(
    name="{{ project_name }}",
    version="{{ version }}",
    description="{{ description }}",
    author="{{ author }}",
    author_email="{{ email }}",
    license="{{ license }}",
    packages=find_packages(where="src", include=["{{ project_name }}", "{{ project_name }}.*"]),
    package_dir={"": "src"},
    install_requires=[],
    python_requires=">=3.9",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
