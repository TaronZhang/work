from setuptools import setup, find_packages

setup(
    name='bid-checker',
    version='1.2.0',
    packages=find_packages(),
    install_requires=[
        'flask>=3.0',
        'python-docx>=1.1',
        'pdfplumber>=0.11',
        'jieba>=0.42',
        'reportlab>=4.2',
        'openai>=1.0',
        'pydantic>=2.0',
        'python-dotenv>=1.0',
    ],
    entry_points={
        'console_scripts': [
            'bid-checker=cli.main:main',
        ],
    },
    python_requires='>=3.10',
)
