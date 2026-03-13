# Prerequisites:
# - Spine Database API: https://github.com/spine-tools/Spine-Database-API
# - Miniconda/Anaconda
# - Brightway:
#       - install by downloading the bw25_env.yml from:
#           - https://learn.brightway.dev/en/latest/content/chapters/BW25/BW25_introduction.html
#           - Create a conda environment with "conda env create -f env_bw25.yml --solver libmamba"
#           - Activate the environment with "conda activate env_bw25"
# - Pandas (if create_xlsx_lca_data_report = True, see below)
# - Optional: Activity Browser
#       - Useful for searching activities and quickly checking their emissions
#       - Does NOT work in the bw25_env.yml environment (requires Brightway 2)
#       - For installation, see "the quick way" here: https://github.com/LCA-ActivityBrowser/activity-browser

'''
Content of bw25_env.yml at the time of writing:
    name: env_bw25
    channels:
        - conda-forge
        - cmutel
    dependencies:
        # core functionality
        - python=3.11 # https://anaconda.org/conda-forge/python/files
        # jupyter
        - jupyterlab=4.2.5 # https://anaconda.org/conda-forge/jupyterlab/files
        # Brightway
        - bw2io=0.9.dev38 # https://anaconda.org/cmutel/bw2io/files
        - bw2calc=2.0.dev22 # https://anaconda.org/cmutel/bw2calc/files
        - bw2data=4.0.dev56 # https://anaconda.org/cmutel/bw2data/files
        - bw2analyzer=0.11.7 # https://anaconda.org/cmutel/bw2analyzer/files
        - stats_arrays=0.7 # https://anaconda.org/conda-forge/stats_arrays/files
        - ecoinvent_interface=2.4.1 # https://anaconda.org/cmutel/ecoinvent_interface/files
        # plotting
        - matplotlib
'''

import os

# ecoinvent settings
ecoinvent_username = '<your Ecoinvent username>'
ecoinvent_password = '<your Ecoinvent password>'
ecoinvent_version = 'ecoinvent-3.11-cutoff'

# brightway settings
brightway_project_name = "bw25-tuto"

orig_model_file_name = 'ne_model.sqlite'
modified_model_file_name = 'ne_model_modified.sqlite'

# path to original ines-spec database file
orig_db_path = os.path.normpath('./' + orig_model_file_name)
orig_url = rf"sqlite:///{orig_db_path}"

# choose a path for you modified model database
modified_db_path = os.path.normpath('./' + modified_model_file_name)
modified_url = rf"sqlite:///{modified_db_path}"

# qty of decimals to round emissions to
round_decimals = 3

# parts of entity names shared by electricity and heat balance nodes, respectively (e.g. NL00_elec or DE00_dheat)
# (used to determine what kind of energy units produce)
elec_node_naming = 'elec'
heat_node_naming = 'dheat'

chosen_lcia_method = 'ReCiPe 2016 v1.03, midpoint (I)'
chosen_ecoinvent_db_version = 'ecoinvent-3.11'

chosen_impact_categories =     [
    'acidification: terrestrial',                                
    'climate change',                                             
    'ecotoxicity: freshwater',                                    
    'ecotoxicity: marine',                                        
    'ecotoxicity: terrestrial',                                   
    'energy resources: non-renewable, fossil',
    'eutrophication: freshwater',
    'eutrophication: marine',
    'human toxicity: carcinogenic',
    'human toxicity: non-carcinogenic',
    'ionising radiation',
    'land use',
    'material resources: metals/minerals',
    'ozone depletion', 
    'particulate matter formation',
    'photochemical oxidant formation: human health',
    'photochemical oxidant formation: terrestrial ecosystems',
    'water use'
]

# TODO: search for location parameter in model
# if exact locations are not found, default locations are searched
default_locations = ['RER', 'GLO', 'RoW'] # put in order of preference
# linking of locations in entity names (left) to Ecoinvent locations (right)
location_links = {
    'FI':'FI', 'Helsinki':'FI', 'Turku':'FI', 'Tampere':'FI', 'Oulu':'FI', 'Jyvaskyla':'FI', 'Vantaa':'FI', 'Espoo':'FI',
    'SE':'SE',
    'NO':'NO',
    'DE':'DE',
    'DK':'DK',
    'PL':'PL',
    'EE':'EE',
    'LV':'LV',
    'LT':'LT',
    'NL':'NL',
    'FR':'FR',
    'BE':'BE',
    'UK':'UK',
    'ES':'ES'
}

# set whether to create a modified model database
create_modified_model_db = True
# when updating ESM input, only add investment emissions for entities that can be invested in
# otherwise add emissions whenever they are available (they will just not be used by the model) # NOTE: check
emissions_to_investable_entities_only = False
# Set if you want report files for the entity-activity pairings and their emission factors
create_txt_lca_data_report = True
create_xlsx_lca_data_report = True

activity_names = {}

# keywords to link parts of Entity names (left) to parts of or full Ecoinvent activity names (right)
# locations are handled separately
keyword_links = {}

# generally applicable keyword links
keyword_links['default'] = {
    'oil':          {'oil'},
    'hfo':          {'oil'}, # hfo exists for heat production but not for electricity in ecoinvent
    'lfo':          {'oil'}, # same for lfo
    'chp':          {'heat and power co-generation'},
    'gas':          {'gas'}, # removed 'natural'    
    'ccgt':         {'gas', 'combined cycle'}, 
    'coal':         {'hard coal'},
    'lignite':      {'lignite'},
    'peat':         {'peat'},
    'diesel':       {'diesel'},
    'biomass':      {'wood'},
    'nuclear':      {'nuclear'},
    'geothermal':   {'geothermal'},
    'wind':         {'wind'},
    'offwind':      {'wind', 'offshore'},
    'offshore':     {'wind', 'offshore'},
    'pv':           {'photovoltaic'},
    'waste':        {'municipal waste incineration'}
}

# keyword links for activity categories
# you can add complete activity names here, or parts of activity names
# complete activity names will override all other keywords

keyword_links['electricity_production'] = {
    'gasold':       {'gas', 'conventional'}, 
    'ocgt':         {'gas', 'conventional'}, # no open cycle gas turbine elec prod in ecoinvent
    'onwind':       {'onshore', 'wind'},
    'onshore':      {'wind', 'onshore'},
    'ror':          {'hydro', 'run-of-river'},
    'reservoir':    {'hydro', 'reservoir'},
    'psclosed':     {'hydro', 'pumped storage'},
    'psopen':       {'hydro', 'pumped storage'},
    'chpwaste':     {}
}
keyword_links['plant_investments'] = {
    'gasocgt':      {'gas power plant construction, 100MW electrical'},
    'ccgtchpgas':   {'gas power plant construction, combined cycle, 400MW electrical'},
    'ocgtchpgas':   {'gas power plant construction, 100MW electrical'},
    'chpwaste':     {'heat and power co-generation unit construction, 1MW electrical, common components for heat+electricity'},
    'chpcoal':      {'heat and power co-generation unit construction, 1MW electrical, common components for heat+electricity'},
    'hob':          {'oil boiler production, 100kW'},
    'boiler':       {'oil boiler production, 100kW'},
    'reservoir':    {'hydropower', 'reservoir'},
    'ror':          {'hydropower', 'run-of-river'}
}

# TODO: let user add custom keyword links
custom_keyword_links = {} # {entity_name_part: {activity_name_part1, activity_name_part2, ...}}
# TODO: search for specific activities (will skip the activity_names dict and directly search from Ecoinvent)
direct_entity_activity_links = {} # {entity_name_part: activity_name}


# --- LISTS OF ACTIVITIES FOR AUTOMATED SEARCHES ---

# activity_categories:
#   working: electricity_production, plant_investments
#   perhaps later: heat_production, link_investments, storage_investments

# activity searches and LCA calculations will take place for these categories only
chosen_activity_categories = ['plant_investments', 'electricity_production']
default_locations = ['RER', 'RoW', 'GLO']

all_keywords = {keyword for value in keyword_links['default'].values() for keyword in value}
for cat in chosen_activity_categories:
    all_keywords.update({keyword for value in keyword_links[cat].values() for keyword in value})

# activity_names forms ready lists that are used for automatic matching of entities to activities.
# automatic matching will limit itself to the activities listed here
# you can add more activities to the lists below
activity_names['electricity_production'] = [
    'electricity production, oil',
    'heat and power co-generation, oil',
    
    'electricity production, natural gas, conventional power plant',
    'electricity production, natural gas, combined cycle power plant',

    'heat and power co-generation, natural gas, conventional power plant, 100MW electrical',
    'heat and power co-generation, natural gas, combined cycle power plant, 400MW electrical',
    'heat and power co-generation, natural gas, mini-plant 2KW electrical',
    'heat and power co-generation, natural gas, 160kW electrical, lambda=1',
    'heat and power co-generation, natural gas, 160kW electrical, Jakobsberg',
    'heat and power co-generation, natural gas, 50kW electrical, lean burn',
    'heat and power co-generation, diesel, 200kW electrical, SCR-NOx reduction',
    'heat and power co-generation, wood chips, 6667 kW, state-of-the-art 2014',
    'heat and power co-generation, biogas, gas engine',

    'electricity production, hard coal',
    'heat and power co-generation, hard coal',
    
    'electricity production, lignite',
    'heat and power co-generation, lignite',
    
    'electricity production, peat', # 30% 100MW, 70% 500MW. capacity / capacity mix is sometimes only mentioned in description.
    
    'electricity production, wood, future',
    
    'electricity, from municipal waste incineration to generic market for electricity, medium voltage',

    'electricity production, nuclear, pressure water reactor',
    'electricity production, nuclear, boiling water reactor',

    'electricity production, deep geothermal',

    'electricity production, hydro, run-of-river',
    'electricity production, hydro, reservoir, alpine region',
    'electricity production, hydro, reservoir, non-alpine region',
    'electricity production, hydro, reservoir, tropical region',
    'electricity production, hydro, pumped storage',

    'electricity production, wind, <1MW turbine, onshore',
    'electricity production, wind, 1-3MW turbine, onshore',
    'electricity production, wind, 1-3MW turbine, offshore',
    'electricity production, wind, >3MW turbine, onshore',

    'electricity production, photovoltaic, 570kWp open ground installation, multi-Si',

    'electricity production, compressed air energy storage',
    'electricity production, compressed air energy storage, adiabatic'
]

activity_names['plant_investments'] = [
    'gas power plant construction, 100MW electrical', # capacity can be interpolated between 100MW and 300MW
    'gas power plant construction, 300MW electrical',
    'gas power plant construction, combined cycle, 400MW electrical',

    'oil power plant construction, 500MW',

    'oil boiler production, 100kW', # Ecoinvent has few alternatives for boilers. Emissions for gas and oil boilers are similar

    'lignite power plant construction', # 30% 100MW, 70% 500MW -> 380MW capacity

    'hard coal power plant construction, 100MW',
    'hard coal power plant construction, 500MW',

    'heat and power co-generation unit construction, 160kW electrical, common components for heat+electricity',
    'heat and power co-generation unit construction, 200kW electrical, common components for heat+electricity',
    'heat and power co-generation unit construction, 1MW electrical, common components for heat+electricity',
    'heat and power co-generation unit construction, 1MWel, 6.4 MWth', # involves a rankine cycle
    'heat and power co-generation unit construction, organic Rankine cycle, 3MW electrical',
    'heat and power co-generation unit construction, 6400kW thermal, common components for heat+electricity',

    'geothermal power plant construction',

    'nuclear power plant construction, pressure water reactor 650MW',
    'nuclear power plant construction, pressure water reactor, 1000MW',
    'nuclear power plant construction, boiling water reactor 1000MW',

    # need both fixed and moving parts
    'wind power plant construction, 800kW, fixed parts', # onshore
    'wind power plant construction, 800kW, moving parts', # onshore
    'wind power plant construction, 2MW, offshore, fixed parts',
    'wind power plant construction, 2MW, offshore, moving parts',
    
    'photovoltaic plant construction, 570kWp, multi-Si, on open ground',
    'concentrated solar power plant construction, solar tower power plant, 20 MW',
    'concentrated solar power plant construction, solar thermal parabolic trough, 50 MW',
    
    # no capacities mentioned for hydro plants, it seems
    # Swiss, mix of types of dams built between 1945 and 1970, therefore they might not be representative for more modern construction, nor for an individual type
    'hydropower plant construction, reservoir', 
    # Swiss reservoir hydropower plants valid for non-alpine region conditions, i.e. all European countries modelled in ecoinvent with hydropower except from Austria, Italy, France and Finland
    'hydropower plant construction, reservoir, non-alpine regions', # all except FI, FR
    'hydropower plant construction, run-of-river', # FI
    'hydropower plant construction, reservoir, alpine region' # FR?
]

# regional differentiation for alpine, non-alpine and ror hydropower
alpine_regions = ['FR']
ror_regions = ['FI'] # in the NE model we assume all Finnish hydropower to be run-of-river

# manual addition of capacities, in MW, for plant investments for which the capacity is not mentioned in the activity name
# for the rest, the capacity is parsed from the activity name
manual_plant_investment_capacities = {
    'lignite power plant construction': 380, # from description: 30% 100MW, 70% 500MW -> 380MW capacity
    'geothermal power plant construction': 5.5, # from reference product name
    'gas boiler production': 0.01, # 10kW, from description,
    'hydropower plant construction, reservoir, non-alpine regions': 175, # 9130/52, from description
    'hydropower plant construction, reservoir, alpine region': 175,
    # ror plants considered in the activity:
    # Rupperswil-Auenstein 45MW, Wildegg-Brugg 25MW, Birsfelden 100MW, Greifenstein 293MW(?),
    # Rheinkraftwerk Albbruck-Dogern 28.5MW, Ruppoldingen 23MW
    # Avg, excluding Greifenstein which may include multiple plants: (45+25+100+28.5+23)/5 = 44.3
    'hydropower plant construction, run-of-river': 50 # rounding up because Greifenstein was not included
}

activity_names['storage_investments'] = [
    # the production of 1 kg of a valve regulated lead acid (VRLA) battery (absorbed glass matt - AGM) for stationary use.
    'battery production, lead acid, rechargeable, stationary', 
    #  production of 1 kg of Li-ion battery pack used e.g. for mechanical drive of an electric vehicle
    'battery production, Li-ion, LFP, rechargeable, prismatic',
    #  e.g. for mechanical drive of an electrical vehicle.
    # The modelled battery has a mass of 280 kg, contains 216 cells and holds a capacity of 32 kWh and thus an energy density of 0.114 kWh/kg
    'battery production, Li-ion, LiMn2O4, rechargeable, prismatic', 
    'battery production, Li-ion, NCA, rechargeable, prismatic',
    'battery production, Li-ion, NMC111, rechargeable, prismatic',
    'battery production, Li-ion, NMC811, rechargeable, prismatic',
    'battery production, NaCl, rechargeable',
    'battery production, NiMH, rechargeable, prismatic'
]

# TODO: add link investments (optional because it's very hard to approximate distances and line types)
# Sophie Pathe, where does she work? Not anymore in Bochum? Or Sharepoint presentations.
# empire has distances between capitals
activity_names['link_investments'] = [
    # NOTE: func unit is "per kilometer"! challenge
    'transmission network construction, electricity, high voltage direct current land cable'
]
