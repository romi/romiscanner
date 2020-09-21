# ROMI Scanner


Gather hardware control of the ROMI 3D scanner as well as the virtual scanner.

The general documentation can be found [here](https://docs.romi-project.eu/Scanner/).

## API documentation
The API documentation is generated automatically using Sphinx & follows the NumPy docstrings style.

For a reference on NumPy docstrings: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/

### Requirements
You will need to install the following dependencies to generate the documentation:
```bash
python3 -m pip install sphinx sphinxcontrib-napoleon sphinx_rtd_theme
```

### Generating the documentation

Edit the RST files and generates the HTML files using:
```bash
make html
```
Note that this should be done from the `doc/` directory at the packages root.

To access the generated API documentation, open `romiscanner/doc/build/html/index.html`:
```bash
firefox build/html/index.html 
```