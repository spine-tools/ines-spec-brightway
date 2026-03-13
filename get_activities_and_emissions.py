# NOTE: use the python environment containing your Brightway installation (e.g. bw25_env)
# Tested with Python 3.11

# from numpy import full
import os
import sys
import re
import datetime
import shutil
import spinedb_api as api
import bw2data as bd
import bw2io as bi
import bw2calc as bc
import importlib.util
from dataclasses import dataclass
from typing import Optional



# Get config file name from command-line argument, default to "config.py" if not provided
if len(sys.argv) > 1:
    config_filename = sys.argv[1]
else:
    print("No config filename specified, defaulting to 'config.py'.")
    config_filename = "config.py"

# define config path and check if it exists
config_path = os.path.join(os.getcwd(), config_filename)
if not os.path.exists(config_path):
    print(f"Config file not found: {config_path}")
    sys.exit(1)

# Import the config file as a module
spec = importlib.util.spec_from_file_location("config", config_path)
print('Printing spec', spec)
if spec and spec.loader:
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
else:
    raise Exception(f'Could not load {config_filename}.')

print('Using config file:', config_path)

# Pandas is only needed if creating an Excel report
if config.create_xlsx_lca_data_report:
    import pandas as pd

# Contains data on an Ecoinvent activity, will be linked to entities
@dataclass
class LCAData:
    '''Class for storing LCA data.'''
    activity_name: str
    # The capacity and location of the capacity related to the activity in Ecoinvent
    activity_capacity: Optional[float] = None
    activity_location: Optional[str] = None
    # comparison of activity location to the location of the linked model Entity
    # can be one of these: correct, default (e.g. RER, RoW, GLO), any, empty
    activity_location_correctness: Optional[str] = None
    # The Brightway activity item
    activity_item: Optional[bd.backends.proxies.Activity] = None
    reference_product: Optional[str] = None
    # contains the chosen LCIA method and impact_category_units (of measurement)
    lcia_info: Optional[dict] = None
    # an identifier of type "('U_SE03_windOnshore', 'SE03_elec') -- wind power plant construction, 800kW, fixed parts -- GLO"
    # used to help link calculated scores to the correct LCAData objects
    act_classifications: Optional[list] = None
    # The activity id in Brightway
    act_id: Optional[str] = None
    technosphere = None
    biosphere = None
    nox_exchanges: Optional[list] = None
    sox_exchanges: Optional[list] = None

    # scores[<impact category>] = (<score>, <extra info on impact category>, <unit of measurement>)
    scores: Optional[dict[str, tuple[float, str, str]]] = None
    # this gives info on whether the scores have been edited
    # e.g. "per activity_capacity" means that scores have been divided by activity_capacity
    scores_edit: Optional[str] = None

@dataclass
class Entity:
    '''Parent class for entities.'''
    entity_byname: Optional[tuple] = None
    parameter_values: Optional[dict] = None
    # will be set True if the entity has an investment_cost parameter
    # used to determine whether the entity can be invested in
    has_investment_cost: Optional[bool] = None
    # keywords are created from Entity names and are used to link activities to entities
    # elec_prod: electricity production activities
    # investment: plant or link investment activities
    elec_prod_keywords: Optional[set] = None
    investment_keywords: Optional[set] = None

    # lca data attributes
    elec_prod_lca: Optional[LCAData] = None
    heat_production_lca: Optional[LCAData] = None
    investment_lca: Optional[LCAData] = None
    #entity_item: Optional[api.db_mapping_base.PublicItem] = None
    #parameter_items: Optional[list[api.db_mapping_base.PublicItem]] = None

# --- Subclasses for specific entity types: Node, Unit, NodeToUnit, UnitToNode, Link ---


@dataclass
class Node(Entity):
    '''Class for storing node data.'''
    entity_class_name = 'node'
    # location of the node, attained from the entity_byname
    location: Optional[str] = None
    #node_type: Optional[str] = None
    output_units: Optional[set[str]] = None
    input_units: Optional[set[str]] = None

    # --- ines-spec parameters: these will filled with EI data, if available ---

    # [ton of CO2/MWh] Implicit CO2 content released when fuel used. Constant or array of periods.
    co2_content: Optional[float] = None
    # [ton of CO2/MWh/year] Emissions caused by the existense of the asset. Constant or array of periods.
    storage_fixed_co2_emissions: Optional[float] = None
    # [ton of CO2/MWh] Emissions embedded in the assets to be constructed. Constant or array of periods.
    storage_investment_co2_emissions: Optional[float] = None 


@dataclass
class Unit(Entity):
    '''Class for storing unit data.'''
    entity_class_name = 'unit'
    location: Optional[str] =   None
    
    # these are the nodes that the unit is connected to
    output_nodes: Optional[set[str]] = None
    input_nodes: Optional[set[str]] = None
    # these are the commodities that the unit produces or consumes
    commodities: Optional[set[str]] = None

    # check whether the unit has electricity or heat output nodes -> determines type of production
    has_elec_output: Optional[bool] = None
    has_heat_output: Optional[bool] = None

    # --- ines-spec parameters ---
    # [ton of CO2/MW/year] Emissions caused by the existense of the asset. Constant or array of periods.
    fixed_co2_emissions: Optional[float] = None
    # [ton of CO2/MW] Emissions embedded in the assets to be constructed. Constant or array of periods.
    investment_co2_emissions: Optional[float] = None # [ton of CO2/MW]


@dataclass
class NodeToUnit(Entity):
    '''Class for storing node to unit data.'''
    entity_class_name = 'node__to_unit'
    from_node: Optional[Node] = None
    to_unit: Optional[Unit] = None

    # --- ines-spec parameters ---
    # [kg of NOx emissions/MWh] NOx emission rate per MWh of flow. Constant.
    nox_emission_rate: Optional[float] = None
    # [kg of SO2 emissions/MWh] SO2 emission rate per MWh of flow. Constant.
    so2_emission_rate: Optional[float] = None


@dataclass
class UnitToNode(Entity):
    '''Class for storing unit to node data.'''
    entity_class_name = 'unit__to_node'
    from_unit: Optional[Unit] = None
    to_node: Optional[Node] = None

    # --- ines-spec parameters ---
    nox_emission_rate: Optional[float] = None
    so2_emission_rate: Optional[float] = None


@dataclass
class Link(Entity):
    '''Class for storing link data'''
    entity_class_name = 'link'
    # --- ines-spec parameters ---
    # [ton of CO2/MW/year] Emissions caused by the existense of the asset. Constant or array of periods.
    fixed_co2_emissions: Optional[float] = None
    # [ton of CO2/MW] Emissions embedded in the assets to be constructed. Constant or array of periods.
    investment_co2_emissions: Optional[float] = None
    capacity: Optional[float] = None # [MW]


# get parameter names and values for a given entity_byname
def get_parameter_values(entity_byname, spine_parameters):
    return {par['parameter_definition_name']:par['parsed_value'] for par in spine_parameters
            if par['entity_byname'] == entity_byname}


# get input and output entities for a Node or Unit object from node__to_unit and unit__to_node
def get_entity_io(spine_entity, spine_entities):
    this_name = spine_entity['entity_byname'][0]
    if spine_entity['entity_class_name'] == 'node': # input/output are units
        input = {i['entity_byname'][0] for i in spine_entities['unit__to_node']
                       if i['entity_byname'][1] == this_name}
        output = {i['entity_byname'][1] for i in spine_entities['node__to_unit']
                        if i['entity_byname'][0] == this_name}
    elif spine_entity['entity_class_name'] == 'unit': # input/output are nodes
        input = {i['entity_byname'][0] for i in spine_entities['node__to_unit']
                       if i['entity_byname'][1] == this_name}
        output = {i['entity_byname'][1] for i in spine_entities['unit__to_node']
                        if i['entity_byname'][0] == this_name}
    else:
        raise Exception('The entity is not a node or unit.')
    return input, output


# create all entity objects based on entity_class_names defined above
def create_entity_objects(spine_entities, spine_parameters):
    entities = {}
    entity_class_map = {'node': Node, 'unit': Unit, 'node__to_unit': NodeToUnit,
                        'unit__to_node': UnitToNode, 'link': Link}

    for entity_class_name, entity_object in entity_class_map.items():
        for spine_entity in spine_entities[entity_class_name]:
            parameter_values = get_parameter_values(spine_entity['entity_byname'], spine_parameters)
            # create Node
            if entity_class_name == 'node':
                input_units, output_units = get_entity_io(spine_entity, spine_entities)
                entities[spine_entity['entity_byname']] = entity_object(
                    entity_byname=spine_entity['entity_byname'],
                    output_units=output_units,
                    input_units=input_units,
                    parameter_values=parameter_values,
                )
            # create Unit
            elif entity_class_name == 'unit':
                input_nodes, output_nodes = get_entity_io(spine_entity, spine_entities)
                entities[spine_entity['entity_byname']] = entity_object(
                    entity_byname = spine_entity['entity_byname'],
                    output_nodes = output_nodes,
                    input_nodes = input_nodes,
                    parameter_values = parameter_values,
                    has_elec_output = any(config.elec_node_naming in output for output in output_nodes),
                    has_heat_output = any(config.heat_node_naming in output for output in output_nodes)
                )
            # create NodeToUnit
            elif entity_class_name == 'node__to_unit':
                entities[spine_entity['entity_byname']] = entity_object(
                    entity_byname = spine_entity['entity_byname'],
                    parameter_values = parameter_values,
                    from_node = spine_entity['entity_byname'][0],
                    to_unit = spine_entity['entity_byname'][1],
                )
            # create UnitToNode
            elif entity_class_name == 'unit__to_node':
                entities[spine_entity['entity_byname']] = entity_object(
                    entity_byname=spine_entity['entity_byname'],
                    parameter_values=parameter_values,
                    from_unit=spine_entity['entity_byname'][0],
                    to_node=spine_entity['entity_byname'][1],
                )
            # create Link
            elif entity_class_name == 'link':
                entities[spine_entity['entity_byname']] = entity_object(
                    entity_byname=spine_entity['entity_byname'],
                    parameter_values=parameter_values,
                )
    
    # set is_investable to True for entities that have an investment_cost parameter
    for e in entities:
            entities[e].is_investable = True if 'investment_cost' in entities[e].parameter_values else False
    
    return entities


def link_entity_keywords(keyword_links: dict[str, set],
                         entities: dict[tuple, Entity],
                         attribute_name: str,
                         append_values: bool = False,
                         overwrite_attribute: bool = False):
    """
    Links keywords to entity objects by matching parts of entity names with predefined keywords.
    
    The function performs case-insensitive matching, prioritizing longer matches. It can either 
    set a single matched value or append multiple matches to the entity's attribute.
    
    Args:
        keyword_links: Dictionary mapping keywords to sets of related values.
                      Example: {'wind': {'wind', 'onshore'}}
        entities: Dictionary of entity objects, keyed by entity name tuples.
        attribute_name: Name of the keyword attribute in the entity objects.
        append_values: If True, appends all matching values to a set.
                      If False, sets only the first matching value.
    
    Notes:
        - Only checks the first element of multi-dimensional entity names
        - Sets empty set as default if no matches found
    
    Example:
        >>> keyword_links = {'wind': {'wind', 'onshore'}}
        >>> entities = {('U_FI00_windOffshore',): Entity()}
        >>> link_entity_keywords(keyword_links, entities, 'ei_keywords', True)
        # Entity.ei_keywords will contain {'wind', 'onshore'}
    """

    # Lowercase keys for case-insensitive matching
    lower_case_links = {key.lower(): value for key, value in keyword_links.items()}
    # Longer substring matches are prioritized
    keys_sorted_by_length = sorted(lower_case_links.keys(), key=len, reverse=True)
    
    for entity_byname, entity_obj in entities.items():
        # NOTE: currently multi-dimensional entity classes may get limited results because we only check entity_name[0]
        parts = entity_byname[0].split('_')
        # Using a set to avoid duplicates
        appended_matches = set()
        
        # Search for the longest case-insensitive substring match
        for part in parts:
            part_lower = part.lower()
            # Check for exact case-insensitive match
            if part_lower in lower_case_links:
                if append_values:
                    appended_matches.update(lower_case_links[part_lower]) 
                else:
                    #if 'link' in entity_byname[0]:
                    #    print('part_lower in lower_case_links:', parts, part_lower, lower_case_links[part_lower])
                    setattr(entity_obj, attribute_name, lower_case_links[part_lower])
                    break
            # Check for the longest case-insensitive substring match
            for key in keys_sorted_by_length:
                if key in part_lower:
                    if append_values:
                        appended_matches.update(lower_case_links[key])
                    else:
                        # Assume that data is at the beginning or end of the part (to avoid erroneous matches)
                        if part_lower.startswith(key) or part_lower.endswith(key):
                            setattr(entity_obj, attribute_name, lower_case_links[key])
                            break
        if append_values:
            # if overwrite_attribute is not True, we add the possibly existing values to appended_matches
            if not overwrite_attribute:
                existing_values = getattr(entity_obj, attribute_name, set())
                if existing_values is None:
                    existing_values = set()
                appended_matches.update(existing_values)
            setattr(entity_obj, attribute_name, appended_matches)
        else:
            if not hasattr(entity_obj, attribute_name):
                setattr(entity_obj, attribute_name, set())  # Default to an empty set if no match is found


# use activity_names[*activity_type*] as argument
def parse_activity_capacities(activities):
    # regex pattern for finding capacities from activity names
    # the regex pattern is unfortunately complex because it looks for ranges of capacities as well, e.g. 1-3MW 
    # \b: Word boundary to ensure we match whole words.
    # \d+: Matches one or more digits.
    # (?:\.\d+)?: Non-capturing group to match an optional decimal part.
    # \s?: Matches an optional whitespace.
    # (?:kW|kWp|MW): Non-capturing group to match the units kW, kWp, or MW.
    # \b at the end ensures the match ends at a word boundary
    number_pattern = r'\d+(?:\.\d+)?'
    unit_pattern = r'kW|kWp|kWe|MW'
    single_capacity_pattern = fr'\b({number_pattern})\s?({unit_pattern})\b'
    range_capacity_pattern = fr'\b({number_pattern})-({number_pattern})\s?({unit_pattern})\b'
    # Combine the patterns
    pattern = fr'{single_capacity_pattern}|{range_capacity_pattern}'
    
    capacities = {}
    for activity in activities:
        matches = re.findall(pattern, activity)
        for match in matches:
            if match[0]:  # Single capacity match
                value = float(match[0])
                unit = match[1]
                if unit in ['kW', 'kWp', 'kWe']:
                    value /= 1000 # convert to MW
                capacities[activity] = value
            # if the capacity is given as a range, we just take the avg of the lower and upper value
            elif match[2] and match[3]:  # Range capacity match
                lower_value = float(match[2])
                upper_value = float(match[3])
                unit = match[4]

                # convert to MW if not already
                if unit in ['kW', 'kWp', 'kWe']:
                    lower_value /= 1000
                    upper_value /= 1000
                
                average_value = (lower_value + upper_value) / 2
                capacities[activity] = average_value
            
        # add manual capacities if available
        if activity in config.manual_plant_investment_capacities:
            capacities[activity] = config.manual_plant_investment_capacities[activity]

    return capacities


# fills in the ei_keywords of entity objects and creates the LCAData object (without results)
# currently we assume that only one activity will be needed per LCAData object
def get_entity_activity_names(entity_dict: dict[tuple, Entity],
                              activity_capacities,
                              activity_category: str,
                              keyword_attribute:str,
                              lca_attribute: str):
    """
    Matches entities with Ecoinvent activities based on keywords and capacities.
    
    Links keywords to entities and creates LCAData objects with appropriate activity names.
    For activities with capacity information, matches the entity with the activity that 
    has the closest capacity rating.

    Args:
        entity_dict: Dictionary mapping entity keys (tuples) to Entity objects
        activity_capacities: Dictionary of activity capacities, keyed by activity category.
        activity_category: Category of activities to search ('electricity_production', 
                         'plant_investments', 'link_investments', etc.)
        keyword_attribute: Name of the attribute in Entity to store keywords ('ei_keywords')
        lca_attribute: Name of LCA attribute to set on entity ('elec_prod_lca', 
                      'heat_prod_lca', 'investment_lca')
    
    Notes:
        - Uses global variables: keyword_links, activity_names, activity_capacities
        - First tries to match activities with capacity information
        - Falls back to first matching activity if no capacity match found
        - Requires entity to have 'capacity' in parameter_values for capacity matching

    Example:
        >>> utns = {e: entities[e] for e in entities 
                   if isinstance(entities[e], UnitToNode)}
        >>> get_entity_activity_names(utns, 'plant_investments', 'investment_lca')
        # Creates LCAData object with matched activity name and capacity
    """
    all_keyword_links = {**config.keyword_links['default'], **config.keyword_links[activity_category]}
    link_entity_keywords(all_keyword_links, entity_dict, keyword_attribute, append_values=True)
    
    entities_without_found_activities = []

    for k,v in entity_dict.items():
        included_keywords = getattr(v, keyword_attribute, set())
        if included_keywords:
            full_activity_match = next((act for act in config.activity_names[activity_category] if act in included_keywords), None)
            
            if full_activity_match:
                # Prioritize the full activity name match
                suitable_activities = [full_activity_match]
            else:
                # keywords not in included_keywords will be avoided (except full activity names)
                all_atomic_keywords = {kw for kw in config.all_keywords if kw not in config.activity_names[activity_category]}
                keywords_avoid = all_atomic_keywords - included_keywords

                # get list of activities that matches all of the keywords
                # re.search makes sure that the keywords match whole words in activity_names
                suitable_activities = [act for act in config.activity_names[activity_category]
                                        if all(re.search(r'\b' + re.escape(kw) + r'\b', act) for kw in included_keywords) and
                                        not any(re.search(r'\b' + re.escape(kw) + r'\b', act) for kw in keywords_avoid)]
            '''
            if 'turbine' in str(v.entity_byname).lower():
                print(f'\nSuitable activities for {k}:', suitable_activities)
                if full_activity_match:
                    print('Full activity match found.')
                print('Included keywords:', included_keywords)
                print('Keywords to avoid:', keywords_avoid, '\n')
            '''
            # filter suitable_activities list to those with capacities
            suitable_activities_cap = {act: activity_capacities[activity_category][act]
                                       for act in suitable_activities
                                       if act in activity_capacities[activity_category]}
            # if suitable_activities_cap has elements, we check the capacity of the unit
            if suitable_activities_cap:
                param_values = v.parameter_values
                utn_capacity = param_values.get('capacity') if param_values else None
                # find the activity with the closest capacity to that of the unit
                closest_capacity = min(suitable_activities_cap.values(), key=lambda x: abs(x - utn_capacity))
                closest_cap_activity = [act for act in suitable_activities_cap
                                        if activity_capacities[activity_category][act] == closest_capacity]
                #print('Unit capacity', unit_capacity, '; Closest cap activity:', closest_cap_activity, '\n')
                chosen_activity = closest_cap_activity[0]
                # set the activity_name attribute based on the closest capacity
                setattr(v,
                        lca_attribute,
                        LCAData(activity_name=chosen_activity, activity_capacity=closest_capacity))
                #entity_dict[e].lca_data = LCAData(activity_name=closest_cap_activity[0])
            elif suitable_activities:
                # if no capacities are found, we just take the first suitable activity (not ideal!)
                #print('No Ecoinvent capacities are found for entity', k)
                # print(suitable_activities)
                # print('')
                setattr(v,
                        lca_attribute,
                        LCAData(activity_name=suitable_activities[0]))
            else:
                # no suitable activities found
                entities_without_found_activities.append((k, included_keywords))
                #entity_dict[e].lca_data = LCAData(activity_name=suitable_activities[0])
                #print('suitable_activities_first_element_type', type(suitable_activities[0]))
        
        #if entities_without_found_activities:
        #    print('No suitable activities found for the following entities:')
        #    for e in entities_without_found_activities:
        #        print(e)
    return entities_without_found_activities


def get_ei_activities(entity_dict:dict[tuple, Entity],
                      eidb,
                      lca_attribute: str,
                      default_locations: list,
                      unit_of_measure: str):
    # Cache for search results (reduces the number of searches)
    search_cache = {}
    
    for e_obj in entity_dict.values():
        activity_name = getattr(e_obj, lca_attribute).activity_name
        #print(f'Entity_byname: {e_obj.entity_byname}, search for activity: {activity_name}')
        
        # Check if the activity_name is already in the cache
        if activity_name not in search_cache:
            search_cache[activity_name] = eidb.search(activity_name, limit=None) 
        
        search_results = search_cache[activity_name]
        
        # Stage 1: search with correct location
        #print(f'Stage 1 with correct location {e_obj.location}.')
        ei_activities = [i for i in search_results
                         if i['location'] == e_obj.location
                         and i['unit'] == unit_of_measure]
        
        # the chosen_activity will remain None if no suitable activity is found
        chosen_activity = None
        
        if ei_activities:
            chosen_activity = ei_activities[0]
            location_correctness = 'correct'
            #print(f'Stage 1: found activity {chosen_activity}.\n')
        
        # Stage 2: search with default locations
        if not ei_activities:
            for default_location in default_locations:
                #print(f'Stage 2 with default location {default_location}.')
                ei_activities = [i for i in search_results
                                 if i['location'] == default_location
                                 and i['unit'] == unit_of_measure]
                if ei_activities:
                    chosen_activity = ei_activities[0]
                    location_correctness = 'default'
                    #print(f'Stage 2: found activity {chosen_activity}.\n')
                    break
        
        # Stage 3: search with any location
        if not ei_activities:
            #print(f'Stage 3 with any location.')
            ei_activities = [i for i in search_results if i['unit'] == unit_of_measure]
            if ei_activities:
                chosen_activity = ei_activities[0]
                location_correctness = 'any'
                #print(f'Stage 3: found activity {chosen_activity}.\n')
        
        if not ei_activities:
            location_correctness = 'empty'
            #print(f'No suitable ei activity found.\n')
        
        if chosen_activity:
            # getattr is like e_obj.lca_attribute but allows for dynamic attribute names
            getattr(e_obj, lca_attribute).activity_item =           chosen_activity
            getattr(e_obj, lca_attribute).reference_product =       chosen_activity['reference product']
            getattr(e_obj, lca_attribute).classifications =         chosen_activity['classifications']

            #print(f'Entity: {e_obj.entity_byname}, '
            #      f'activity: {getattr(e_obj, lca_attribute).activity_name}, '
            #      f'location: {chosen_activity["location"]}')
        else:
            print('No activity found for entity:', e_obj.entity_byname)
        
        getattr(e_obj, lca_attribute).location_correctness =    location_correctness


def calculate_lcas(entity_dict:dict[tuple, Entity], lca_attribute:str, impact_cat_units):
    #print('Preparing for LCA calculations.')
    impact_categories = [m for m in bd.methods
                         if m[0] == config.chosen_ecoinvent_db_version
                         and m[1] == config.chosen_lcia_method
                         and m[2] in config.chosen_impact_categories]
    
    lca_activities = {e.entity_byname : getattr(e, lca_attribute).activity_item for e in entity_dict.values()}
    if not lca_activities:
        raise ValueError("No lca activities found. Check that your entity/activity matching is working and not empty.")
    
    if lca_attribute == 'elec_prod_lca':
        assert [act['unit'] == 'kilowatt hour' for act in lca_activities.values()]
    if lca_attribute == 'investment_lca':
        assert [act['unit'] == 'unit' for act in lca_activities.values()]
    
    technosphere_flows = {e.entity_byname : list(getattr(e, lca_attribute).activity_item.technosphere())
                          for e in entity_dict.values()}
    biosphere_flows = {e.entity_byname : list(getattr(e, lca_attribute).activity_item.biosphere())
                       for e in entity_dict.values()}
    #functional_units = {e_byname[0]: {act['id']: 1} for e_byname, act in lca_activities.items()}
    functional_units = {f'{e_byname} -- {act["name"]} -- {act["location"]}': {act['id']: 1}
                        for e_byname, act in lca_activities.items()}
    method_config = {"impact_categories":impact_categories}
    data_objs = bd.get_multilca_data_objs(functional_units=functional_units, method_config=method_config)

    #print('Performing LCA calculations.')
    mlca = bc.MultiLCA(demands=functional_units, method_config=method_config, data_objs=data_objs)
    mlca.lci()
    mlca.lcia()

    #print('Linking LCA data to LCAData objects.')
    # Preprocess scores into a dictionary indexed by entity_byname
    scores_by_entity = {}
    for score_key, score_value in mlca.scores.items():
        # entity_key is the entity_byname defined in functional_units
        entity_key = score_key[1].split(' -- ')[0]
        if entity_key not in scores_by_entity:
            scores_by_entity[entity_key] = {}
        scores_by_entity[entity_key][score_key] = score_value

    for k,v in entity_dict.items():
        lca_data = getattr(v, lca_attribute)
        lca_data.technosphere = technosphere_flows[k]
        lca_data.biosphere = biosphere_flows[k]
        
        nox_flows = [flow for flow in biosphere_flows[k]
                     if all(keyword in flow.input['name'].lower() for keyword in ['nitrogen', 'oxide'])]
        sox_flows = [flow for flow in biosphere_flows[k]
                     if all(keyword in flow.input['name'].lower() for keyword in ['sulfur', 'oxide'])]
        
        # unit check
        if len(nox_flows + sox_flows) > 0:
            assert [flow['unit'] == 'kilogram' for flow in nox_flows + sox_flows]
        
        total_nox = sum(flow['amount'] for flow in nox_flows) * 1000 # convert kg/kWh to kg/MWh (ines-spec unit for nox_emission_rate)
        total_sox = sum(flow['amount'] for flow in sox_flows) * 1000

        # k[0][2] is the impact category (e.g. 'climate change'), v is (score, act_location)
        # k[0][3] gives extra info on the impact category (e.g. 'global warming potential (GWP20)')
        # impact_category_units[k[0][2]] provides the unit for the impact category
        # score values are retrieved with lca_data.scores[<impact category>][0]
        lca_data.scores = {k[0][2] : (v, k[0][3], impact_cat_units[k[0][2]]) for k,v in scores_by_entity.get(str(k), {}).items()}
        lca_data.scores_edit = 'orig' # indicates that the scores are original from Ecoinvent and not edited by the script
        lca_data.nox_exchanges = total_nox
        lca_data.sox_exchanges = total_sox
        lca_data.act_id = list(scores_by_entity[str(k)].keys())[0][1]
        lca_data.activity_location = getattr(v, lca_attribute).activity_item['location']
        
        # assert that location in score matches location of previously assigned activity item
        score_location = list(scores_by_entity[str(k)].keys())[0][1].split(' -- ')[2]
        assert lca_data.activity_location == score_location
        
        lca_data.lcia_settings = {
            'method': config.chosen_lcia_method,
            'impact_category_units': impact_cat_units
        }


# for scores for which the unit (of measurement) is 'unit' (piece):
# we need to divide the score by the capacity of the activity to get emissions per MWh
def divide_investment_scores_by_capacity(all_entities: dict[tuple, Entity]):
    """
    Divides investment LCA scores by the activity capacity if the unit of the activity item is 'unit'.
    This is to convert emissions from per unit to emissions per MWh of capacity constructed.
    """
    for e_key, e_value in all_entities.items():
        inv_lca = e_value.investment_lca
        if not (inv_lca and inv_lca.activity_item):
            continue
        if inv_lca.activity_item['unit'] != 'unit':
            continue
        if not inv_lca.activity_capacity:
            print(f'No activity capacity for {e_key} with activity "{inv_lca.activity_item["name"]}".\nThe scores will be set to None.')
            inv_lca.scores = None
            inv_lca.scores_edit = 'None due to no activity capacity'
            continue
        if inv_lca.scores_edit != 'orig':
            print(f'Investment LCA scores for {e_key} already edited, skipping division by capacity.')
            continue
        if inv_lca.scores is None:
            continue

        for score_key, score_value in inv_lca.scores.items():
            # kg CO2-eq per unit -> div by capacity [MW] -> kg CO2-eq per MW
            # -> div by 1000 -> ton CO2-eq per MWh (ines-spec unit for investment_co2_emissions)
            new_value = (
                (score_value[0] / inv_lca.activity_capacity) / 1000,
                score_value[1],
                f'{score_value[2].replace("kg", "ton")} / MW'
            )
            inv_lca.scores[score_key] = new_value
        inv_lca.scores_edit = 'per_activity_capacity'


def add_investment_co2_emissions(entity_dict:dict):
    with api.DatabaseMapping(config.modified_url) as db_map:
        # add investments
        if db_map:
            for e in entity_dict.values():
                if not e.entity_byname:
                    print(f'Warning: entity {e} has no entity_byname!')
                    continue
                if isinstance(e, UnitToNode) and 'elec' in e.entity_byname[1] and e.investment_lca and e.investment_lca.scores:
                    unit_name = e.entity_byname[0]
                    # Check for an existing parameter value before adding a new one                
                    existing = db_map.get_parameter_value_items(
                        parameter_definition_name="investment_co2_emissions",
                        entity_byname=(unit_name,)
                    )

                    if not existing:
                        db_map.add_parameter_value(
                            entity_class_name="unit",
                            entity_byname=(unit_name,),
                            parameter_definition_name="investment_co2_emissions",
                            alternative_name="Base",
                            parsed_value=round(e.investment_lca.scores['climate change'][0], config.round_decimals),
                        )
                    else:
                        answer = input(
                            f"Value for parameter \"investment_co2_emissions\" in unit {unit_name} already exists. Overwrite? (y/n): "
                        )
                        if answer.lower() == 'y':
                            db_map.update_parameter_value(
                                entity_class_name="unit",
                                entity_byname=(unit_name,),
                                parameter_definition_name="investment_co2_emissions",
                                alternative_name="Base",
                                parsed_value=round(e.investment_lca.scores['climate change'][0], config.round_decimals)
                            )
            # save changes to the database
            db_map.commit_session("Added investment_co2_emissions parameter values.")
        else:
            raise Exception("Database mapping failed. Cannot add parameter values.")


def report_in_excel(lca_entities, lca_attribute, filename_prefix="lca_data_report", entities_without_acts=None):
    """
    Writes LCA results for a list of entities to an Excel file.
    lca_entities: list of entities (e.g. UnitToNode) with the relevant LCA attribute set
    lca_attribute: string, e.g. 'investment_lca' or 'elec_prod_lca'
    filename_prefix: string, e.g. 'investment' or 'electricity_production'
    entities_without_acts: list of (entity_byname, keywords) tuples for which no activity was found
    """
    if not config.create_xlsx_lca_data_report:
        return

    # Collect all unique impact categories and their units
    impact_categories_units = {}
    for e in lca_entities:
        lca_data = getattr(e, lca_attribute)
        if lca_data and lca_data.scores:
            for ic, score in lca_data.scores.items():
                if ic not in impact_categories_units:
                    impact_categories_units[ic] = score[2]  # score[2] is the unit

    # column names for the impact categories
    impact_columns = [f"{ic} [{impact_categories_units[ic]}]" for ic in impact_categories_units]

    # Prepare data for DataFrame
    rows = []
    for e in lca_entities:
        lca_data = getattr(e, lca_attribute)
        if not lca_data or not lca_data.scores:
            continue
        row = {
            "Entity": str(e.entity_byname),
            "Activity name": lca_data.activity_name,
            "Capacity [MW]": lca_data.activity_capacity if lca_data.activity_capacity else None,
            "Location": lca_data.activity_location if lca_data.activity_location else None
        }
        for ic in impact_categories_units:
            value = lca_data.scores.get(ic, (None, None, None))[0]
            row[f"{ic} [{impact_categories_units[ic]}]"] = value
        rows.append(row)

    other_columns = [i for i in rows[0].keys() if i not in impact_columns]
    df = pd.DataFrame(rows, columns = other_columns + impact_columns)

    # Prepare missing activities DataFrame
    if entities_without_acts:
        missing_rows = [
            {"Entity": str(entity), "Included keywords": str(keywords)}
            for entity, keywords in entities_without_acts
        ]
        missing_df = pd.DataFrame(missing_rows, columns=["Entity", "Included keywords"])
    else:
        missing_df = pd.DataFrame(columns=["Entity", "Included keywords"])

    # Write the DataFrame to Excel with two sheets
    excel_path = os.path.join(os.getcwd(), fr"output\{filename_prefix}_lca_data_report.xlsx")
    with pd.ExcelWriter(excel_path) as writer:
        df.to_excel(writer, index=False, sheet_name="LCA Data")
        missing_df.to_excel(writer, index=False, sheet_name="Missing Activities")
    print(f"Excel report written to {excel_path}")


def report_in_txt(lca_entities, lca_attribute, filename_prefix="lca_data_report", entities_without_acts=None):
    """
    Writes LCA results for a list of entities to a .txt file.
    lca_entities: list of entities (e.g. UnitToNode) with the relevant LCA attribute set
    lca_attribute: string, e.g. 'investment_lca' or 'elec_prod_lca'
    filename_prefix: string, e.g. 'investment' or 'electricity_production'
    entities_without_acts: list of (entity_byname, keywords) tuples for which no activity was found
    """
    if not config.create_txt_lca_data_report:
        return

    txt_report_filename = f"{filename_prefix}_lca_data_report.txt"
    txt_report_path = os.path.join(os.getcwd(), fr'output\{txt_report_filename}')

    with open(txt_report_path, "w", encoding="utf-8") as report_file:
        report_file.write(f"LCA Data Report ({filename_prefix})\nGenerated: {datetime.datetime.now()}\n\n")
        # Write missing activities at the top
        if entities_without_acts:
            report_file.write("Entities without suitable activities:\n")
            for entity, keywords in entities_without_acts:
                report_file.write(f"Entity: {entity}, Included keywords: {keywords}\n")
            report_file.write('\n')
        ic_width = 65
        value_width = 15
        unit_width = 20
        separator_width = 120
        for e in lca_entities:
            lca_data = getattr(e, lca_attribute)
            if not lca_data or not lca_data.scores:
                continue
            report_file.write('-' * separator_width + '\n')
            report_file.write(f"Entity: {e.entity_byname}\n")
            report_file.write(f"Activity: {lca_data.activity_name}\n")
            report_file.write('-' * separator_width + '\n')
            report_file.write(f"{'Impact category':{ic_width}} {'Value':{value_width}} {'Unit':{unit_width}}\n")
            report_file.write('-' * separator_width + '\n')
            for ic, score in lca_data.scores.items():
                report_file.write(
                    f"{ic:{ic_width}} "
                    f"{score[0]:<{value_width}.6g} "
                    f"{score[2]:{unit_width}}\n"
                )
            report_file.write('\n\n')
    print(f"TXT report written to {txt_report_path}")


def main():

    #  --- Set current Brightway project ---
    bd.projects.set_current(config.brightway_project_name)

    if config.ecoinvent_version in bd.databases:
        print(f'{config.ecoinvent_version} is already present in the project')
    else:
        bi.import_ecoinvent_release(
            version =       config.ecoinvent_version.split('-')[1], # e.g. 3.11
            system_model =  config.ecoinvent_version.split('-')[2], # can be cutoff / apos / consequential / EN15804
            username =      config.ecoinvent_username,
            password =      config.ecoinvent_password
        )

    eidb = bd.Database(config.ecoinvent_version)
    print("The imported ecoinvent database is of type {} and has a length of {}.".format(type(eidb), len(eidb)))

    # --- Create modified model database if needed ---

    # Ensure the output directory exists
    os.makedirs(os.path.normpath('./output/'), exist_ok=True)

    # Copy the original database to a new file
    if config.create_modified_model_db:
        print(f'Creating a copy of the original database {config.orig_db_path}...')
        if not os.path.exists(config.orig_db_path):
            raise FileNotFoundError(f"Original database file {config.orig_db_path} does not exist.")
        if os.path.exists(config.modified_db_path):
            user_input = input((f'\nWarning: Modified database file {config.modified_db_path} already exists. Do you want to overwrite it? (y/n) '))
            if user_input.lower() == 'y':
                os.remove(config.modified_db_path)
            else:
                raise Exception(f"\nCannot proceed without overwriting the existing modified database file {config.modified_db_path}.")
        print(f'Creating copy of {config.orig_model_file_name} with name {config.modified_model_file_name}...')
        shutil.copyfile(config.orig_db_path, config.modified_db_path)

    assert len(config.chosen_activity_categories) > 0, "No activity categories chosen! Please set 'chosen_activity_categories' in config.py."
    
    #bd.projects.set_current(config.brightway_project_name)
    #eidb = bd.Database(config.ecoinvent_version)

    spine_parameters = []
    spine_entities = {}
    # the parameters of interest in ines-spec
    parameter_names = ['investment_cost', 'storage_investment_cost', 'capacity', 'node_type']
    # entity classes in ines-spec
    entity_class_names = {'node', 'unit', 'node__to_unit', 'unit__to_node', 'link'}

    with api.DatabaseMapping(config.orig_url) as db_map:
        # get parameter value items for each parameter name
        for parameter_name in parameter_names:
            spine_parameters += db_map.get_parameter_value_items(parameter_definition_name=parameter_name)
        # get spine entities for each chosen entity class name
        for entity_class_name in entity_class_names:
            spine_entities[entity_class_name] = db_map.get_entity_items(entity_class_name=entity_class_name)
    
    print('Loading entity data from model...')
    all_entities = create_entity_objects(spine_entities, spine_parameters)
        
    link_entity_keywords(config.location_links, all_entities, 'location')
    
    activity_capacities = {}
    for at in config.chosen_activity_categories:
        activity_capacities[at] = parse_activity_capacities(config.activity_names[at])
    
    # Retrieve units of measurement for the chosen impact categories
    impact_category_units = {
        m[2]:bd.Method(m).metadata['unit'] for m in bd.methods
        if m[1] == config.chosen_lcia_method and m[2] in config.chosen_impact_categories
    }

    # activity categories: electricity_production, plant_investments, link_investments
    # lca_attributes: elec_prod_lca, heat_prod_lca, investment_lca
    # the function links entity names to activities and returns a list of entities that do not have suitable activities
    if 'electricity_production' in config.chosen_activity_categories:
        print('Getting entity activity names for electricity_production...')
            # UnitToNode objects that have an elec node
        utns_with_elec_node = {
            e:all_entities[e] for e in all_entities
            if isinstance(all_entities[e], UnitToNode) and config.elec_node_naming in e[1]
        }
        elec_entities_without_acts = get_entity_activity_names(utns_with_elec_node,
                                                            activity_capacities,
                                                            'electricity_production',
                                                            'elec_prod_keywords',
                                                            'elec_prod_lca')
        #if elec_entities_without_acts:
        #    print('\nNo suitable activities found for the following entities (electricity production):\n')
        #    for e in elec_entities_without_acts:
        #        print(e)
        #    print('')
        
        utns_with_elec_prod_lca = {
            e: all_entities[e] for e in all_entities
            if isinstance(all_entities[e], UnitToNode)
            and 'elec' in all_entities[e].entity_byname[1]
            and all_entities[e].elec_prod_lca
        }

        print('Matching electricity production activities with entities...')
        get_ei_activities(utns_with_elec_prod_lca, eidb, 'elec_prod_lca', config.default_locations, 'kilowatt hour')

        print('Performing LCA calculations for electricity production...')
        calculate_lcas(utns_with_elec_prod_lca, 'elec_prod_lca', impact_category_units)

        utns_with_elec_prod_lca = [
            e for e in all_entities.values()
            if isinstance(e, UnitToNode)
            and 'elec' in e.entity_byname[1]
            and e.elec_prod_lca and e.elec_prod_lca.scores
        ]
         
        report_in_excel(
            utns_with_elec_prod_lca, 'elec_prod_lca', filename_prefix="electricity_production",
            entities_without_acts=elec_entities_without_acts
        )
        report_in_txt(
            utns_with_elec_prod_lca, 'elec_prod_lca', filename_prefix="electricity_production",
            entities_without_acts=elec_entities_without_acts
        )
        
    
    if 'plant_investments' in config.chosen_activity_categories:
        all_utns = {e:all_entities[e] for e in all_entities if isinstance(all_entities[e], UnitToNode)}
        print('Getting entity activity names for plant_investments...')
        inv_entities_without_acts = get_entity_activity_names(all_utns,
                                                            activity_capacities,
                                                            'plant_investments',
                                                            'investment_keywords',
                                                            'investment_lca')
        
        utns_with_investment_lca = {
            e: all_entities[e] for e in all_entities
            if isinstance(all_entities[e], UnitToNode)
            and all_entities[e].investment_lca
        }

        print('Matching investment activities with entities...')
        get_ei_activities(utns_with_investment_lca, eidb, 'investment_lca', config.default_locations, 'unit')

        print('Performing LCA calculations for power plant investments...')
        calculate_lcas(utns_with_investment_lca, 'investment_lca', impact_category_units)

        print('Dividing plant investment scores by unit capacity to get emissions per MW...')
        divide_investment_scores_by_capacity(all_entities)

        utns_with_investment_lca = [
            e for e in all_entities.values()
            if isinstance(e, UnitToNode)
            and e.investment_lca and e.investment_lca.scores
        ]

        if config.create_modified_model_db:
            print('Adding investment_co2_emissions to model input...')
            add_investment_co2_emissions(all_entities)

        report_in_excel(
            utns_with_investment_lca, 'investment_lca', filename_prefix="investment",
            entities_without_acts=inv_entities_without_acts
        )
        report_in_txt(
            utns_with_investment_lca, 'investment_lca', filename_prefix="investment",
            entities_without_acts=inv_entities_without_acts
        )


if __name__ == "__main__":
    main()
