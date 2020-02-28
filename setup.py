from setuptools import setup, find_packages

setup(
    name="scanoss-webhook-integration",
    version="0.6.1",
    author="SCANOSS",
    author_email="info@scanoss.co.uk",
    setup_requires=["pytest-runner"],
    tests_require=["pytest", "grappa"],
    install_requires=["requests", "crc32c", "pyyaml", "pyjwt[crypto]"],
    entry_points={
        'console_scripts': ['scanoss-hook=scanoss.command_line:main'],
    },
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent"
    ],
    python_requires='>=3.5'
)
