from setuptools import setup, find_packages

setup(
    name='kaniko-build',
    author="yinheli",
    author_email="me@yinheli.com",
    version='0.1.0',
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires=[
        'Click',
        'Jinja2',
    ],
    entry_points={
        'console_scripts': [
            'kaniko-build = kanikobuild.cli:cli',
        ],
    },
)
