# ines-spec-brightway
Using Brightway for automated integration of emissions into energy system models in ines-spec format.

# Overview

Goals
* Automated calculation of environmental impacts from operations and investments in energy system models
* Reduction of manual LCA work in energy system modelling
* Customisability and operability with many types of models (in ines-spec format)

Features
* Accesses the Ecoinvent database
  * Retrieves emission data on power plant construction, electricity and heat production, transmission link construction, battery production and more
* Choice of impact assessment method and Ecoinvent database version
* Updates emission data to energy system model input

The emission tool works with energy system models in ines-spec format
* A standardized data format for energy system models
* Enables interoperability between different energy modelling tools and platforms

# User guide (under construction)

## Prerequisites
* Spine Database API: https://github.com/spine-tools/Spine-Database-API
* Miniconda/Anaconda
* Brightway
  * install by downloading the bw25_env.yml from:
    * https://learn.brightway.dev/en/latest/content/chapters/BW25/BW25_introduction.html
    * Create a conda environment with "conda env create -f env_bw25.yml --solver libmamba"
    * Activate the environment with "conda activate env_bw25"
* Pandas (if `create_xlsx_lca_data_report = True` in `config.py`)
* Energy system model input
  * Currently, the tool only supports the North European model (https://github.com/vttresearch/north_european_model)
  * The inputData file needs to converted into `.sqlite` in ines-spec format
* Optional: Activity Browser
  * Useful for searching activities and quickly checking their emissions
  * Does NOT work in the bw25_env.yml environment (requires Brightway 2)
  * For installation, see "the quick way" here: https://github.com/LCA-ActivityBrowser/activity-browser

 ## File descriptions

`config.py`
* The main file for settings
* enter your Ecoinvent username, password and version here.

`get_activities_and_emissions.py`
* Does the actual work: searches for emission data from Ecoinvent activities and feeds them to the energy system model input.  
