from __future__ import absolute_import, print_function

requires = [
    "flask>=0.10.1"
]

config = {
    'name': 'fake',
    'version': '0.0.1',
    'description': 'fake services to launch anything',
    'author': 'Thomas Rampelberg',
    'author_email': 'thomas@mesosphere.io',

    'packages': [
        'fake'
    ],
    'entry_points': {
    },
    'setup_requires': [
    ],
    'install_requires': requires,
    'dependency_links': [
    ],
    'tests_require': [
    ],
    'scripts': [
    ]
}

if __name__ == "__main__":
    from setuptools import setup

    setup(**config)
