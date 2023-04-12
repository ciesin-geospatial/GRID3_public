"""
This file contains country data type dictionaries that are useful and do not change much

This file should be fairly static only if a new country or data type is being added, should we edit this file.
"""
country_filename = {'AGO': 'Angola', 'BDI': 'Burundi', 'BEN': 'Benin', 'BFA': 'Burkina_Faso', 'BWA': 'Botswana',
                    'CAF': 'Central_African_Republic', 'CIV': "Cote_dIvoire", 'CMR': 'Cameroon', 'COD': 'COD',
                    'COG': 'Republic_of_the_Congo', 'COM': 'Comoros', 'CPV': 'Cabo_Verde', 'DJI': 'Djibuti',
                    'ERI': 'Eritrea', 'ESH': 'Western_Sahara', 'ETH': 'Ethiopia', 'GAB': 'Gabon', 'GHA': 'Ghana',
                    'GIN': 'Guinea', 'GMB': 'The_Gambia', 'GNB': 'Guinea_Bissau', 'GNQ': 'Equatorial_Guinea',
                    'KEN': 'Kenya', 'LBR': 'Liberia', 'LSO': 'Lesotho', 'MDG': 'Madagascar', 'MLI': 'Mali',
                    'MOZ': 'Mozambique', 'MRT': 'Mauritania', 'MUS': 'Mauritius', 'MWI': 'Malawi',
                    'NAM': 'Namibia', 'NER': 'Niger', 'NGA': 'Nigeria', 'REU': 'Reunion', 'RWA': 'Rwanda',
                    'SDN': 'Sudan', 'SEN': 'Senegal', 'SLE': 'Sierra_Leone', 'SOM': 'Somalia', 'SSD': 'South_Sudan',
                    'STP': 'Sao_Tome_and_Principe', 'SWZ': 'Eswatini', 'SYC': 'Seychelles', 'TCD': 'Chad',
                    'TGO': 'Togo', 'TZA': 'Tanzania', 'UGA': 'Uganda', 'ZAF': 'South_Africa', 'ZMB': 'Zambia',
                    'ZWE': 'Zimbabwe'}

country_name = {'AGO': 'Angola', 'BDI': 'Burundi', 'BEN': 'Benin', 'BFA': 'Burkina Faso', 'BWA': 'Botswana',
                'CAF': 'Central African Republic', 'CIV': "Côte d'Ivoire", 'CMR': 'Cameroon', 'COD': 'COD',
                'COG': 'Republic of the Congo', 'COM': 'Comoros', 'CPV': 'Cabo Verde', 'DJI': 'Djibuti',
                'ERI': 'Eritrea', 'ESH': 'Western Sahara', 'ETH': 'Ethiopia', 'GAB': 'Gabon', 'GHA': 'Ghana',
                'GIN': 'Guinea', 'GMB': 'The Gambia', 'GNB': 'Guinea Bissau', 'GNQ': 'Equatorial Guinea',
                'KEN': 'Kenya', 'LBR': 'Liberia', 'LSO': 'Lesotho', 'MDG': 'Madagascar', 'MLI': 'Mali',
                'MOZ': 'Mozambique', 'MRT': 'Mauritania', 'MUS': 'Mauritius', 'MWI': 'Malawi', 'NAM': 'Namibia',
                'NER': 'Niger', 'NGA': 'Nigeria', 'REU': 'Réunion', 'RWA': 'Rwanda', 'SDN': 'Sudan', 'SEN': 'Senegal',
                'SLE': 'Sierra_Leone', 'SOM': 'Somalia', 'SSD': 'South_Sudan', 'STP': 'Sao Tome and Principe',
                'SWZ': 'Eswatini', 'SYC': 'Seychelles', 'TCD': 'Chad', 'TGO': 'Togo', 'TZA': 'Tanzania',
                'UGA': 'Uganda', 'ZAF': 'South Africa', 'ZMB': 'Zambia', 'ZWE': 'Zimbabwe'}

poi_data_type = {'health_facility': 'g3_hltfac',
                 'school': 'g3_school',
                 'settlement': 'g3_settl',
                 'religious_cnt': 'g3_relcnt'}

country_boundaries = {
    # COD
    "cod": {'boundary0': 'g3_cntry', 'boundary1': 'g3_prov', 'boundary2': 'g3_ant', 'boundary3': 'g3_zs','boundary4': 'g3_as'},
    # SLE
    "sle": {'boundary0': 'g3_cntry', 'boundary1': 'g3_prov', 'boundary2': 'g3_dist', 'boundary3': 'g3_chief', 'boundary4': 'g3_sec'},
    # NGA
    "nga": {'boundary0': 'g3_cntry', 'boundary1': 'g3_state', 'boundary2': 'g3_lga', 'boundary3': 'g3_ward', 'boundary4': 'NA'},
    # MOZ
    "moz": {'boundary0': 'g3_cntry', 'boundary1': 'g3_prov', 'boundary2': 'g3_dist', 'boundary3': 'g3_posto', 'boundary4': 'NA'},
    # ZMB
    "zmb": {'boundary0': 'g3_cntry', 'boundary1': 'g3_prov', 'boundary2': 'g3_dist', 'boundary3': 'g3_ward', 'boundary4': 'NA'},
    # BFA
    "bfa": {'boundary0': 'g3_cntry', 'boundary1': 'g3_regn', 'boundary2': 'g3_distsan', 'boundary3': 'g3_comm', 'boundary4': 'NA'}
}
