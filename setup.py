from setuptools import setup, find_packages

setup(
    name="highfinesse",
    install_requires=["sipyco"],
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "aqctl_highfinesse = highfinesse.aqctl_highfinesse:main",
        ],
    },
)

