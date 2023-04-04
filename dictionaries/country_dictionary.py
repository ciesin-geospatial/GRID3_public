"""
This file contains country data type dictionaries that are useful and do not change much

This file should be fairly static only if a new country or data type is being added, should we edit this file.
"""
country_filename = {'AGO': 'Angola', 'BDI': 'Burundi', 'BEN': 'Benin', 'BFA': 'Burkina_Faso', 'BWA': 'Botswana',
                    'CAF': 'Central_African_Republic', 'CIV': "Cote_dIvoire", 'CMR': 'Cameroon', 'COD': 'COD',
                    'COG': 'Republic_of_the_Congo', 'COM': 'Comoros', 'Cabo_Verde':'CPV','DJI': 'Djibuti',
                    'ERI': 'Eritrea', 'ESH': 'Western_Sahara', 'ETH': 'Ethiopia','GAB':'Gabon', 'GHA': 'Ghana',
                    'GIN': 'Guinea','GMB':'The_Gambia', 'GNB': 'Guinea_Bissau', 'GNQ': 'Equatorial_Guinea',
                    'KEN': 'Kenya', 'LBR': 'Liberia', 'LSO': 'Lesotho', 'MDG': 'Madagascar','MLI': 'Mali',
                    'MOZ': 'Mozambique', 'MRT': 'Mauritania','MUS':'Mauritius', 'NAM': 'Namibia', 'NER': 'Niger',
                    'NGA': 'Nigeria', 'REU': 'Reunion', 'RWA': 'Rwanda', 'SDN': 'Sudan', 'SEN': 'Senegal',
                    'SLE': 'Sierra_Leone', 'SOM': 'Somalia', 'SSD': 'South_Sudan', 'STP':'Sao_Tome_and_Principe',
                    'SWZ': 'Eswatini','SYC': 'Seychelles', 'TCD': 'Chad', 'TGO': 'Togo', 'TZA': 'Tanzania',
                    'UGA': 'Uganda', 'ZAF':'South_Africa','ZMB': 'Zambia', 'ZWE': 'Zimbabwe'}

country_name = {'AGO': 'Angola', 'BDI': 'Burundi', 'BEN': 'Benin', 'BFA': 'Burkina Faso', 'BWA': 'Botswana',
                    'CAF': 'Central African Republic', 'CIV': "Côte d'Ivoire", 'CMR': 'Cameroon', 'COD': 'COD',
                    'COG': 'Republic of the Congo', 'COM': 'Comoros', 'Cabo Verde':'CPV','DJI': 'Djibuti',
                    'ERI': 'Eritrea', 'ESH': 'Western Sahara', 'ETH': 'Ethiopia','GAB':'Gabon', 'GHA': 'Ghana',
                    'GIN': 'Guinea','GMB':'The Gambia', 'GNB': 'Guinea Bissau', 'GNQ': 'Equatorial Guinea',
                    'KEN': 'Kenya', 'LBR': 'Liberia', 'LSO': 'Lesotho', 'MDG': 'Madagascar','MLI': 'Mali',
                    'MOZ': 'Mozambique', 'MRT': 'Mauritania','MUS':'Mauritius', 'NAM': 'Namibia', 'NER': 'Niger',
                    'NGA': 'Nigeria', 'REU': 'Réunion', 'RWA': 'Rwanda', 'SDN': 'Sudan', 'SEN': 'Senegal',
                    'SLE': 'Sierra_Leone', 'SOM': 'Somalia', 'SSD': 'South_Sudan', 'STP':'Sao Tome and Principe',
                    'SWZ': 'Eswatini','SYC': 'Seychelles', 'TCD': 'Chad', 'TGO': 'Togo', 'TZA': 'Tanzania',
                    'UGA': 'Uganda', 'ZAF':'South Africa','ZMB': 'Zambia', 'ZWE': 'Zimbabwe'}

poi_data_type = {'health_facility': 'g3_hltfac', 'school': 'g3_school', 'settlement': 'g3_settl', 'religious_cnt': 'g3_relcnt'}

country_boundaries = {
    # COD
    "cod": {'boundary0': 'cod_cntry', 'boundary1': 'cod_prov', 'boundary2': 'cod_ant', 'boundary3': 'cod_zs','boundary4': 'cod_as'},
    # SLE
    "sle": {'boundary0': 'sle_cntry', 'boundary1': 'sle_prov', 'boundary2': 'sle_dist', 'boundary3': 'sle_chief', 'boundary4': 'sle_sec'},
    # NGA
    "nga": {'boundary0': 'nga_cntry', 'boundary1': 'nga_state', 'boundary2': 'nga_lga', 'boundary3': 'nga_ward', 'boundary4': 'NA'},
    # MOZ
    "moz": {'boundary0': 'moz_cntry', 'boundary1': 'moz_prov', 'boundary2': 'moz_dist', 'boundary3': 'moz_posto', 'boundary4': 'NA'},
    # ZMB
    "zmb": {'boundary0': 'zmb_cntry', 'boundary1': 'zmb_prov', 'boundary2': 'zmb_dist', 'boundary3': 'zmb_ward', 'boundary4': 'NA'},
    # BFA
    "bfa": {'boundary0': 'bfa_cntry', 'boundary1': 'bfa_regn', 'boundary2': 'bfa_distsan', 'boundary3': 'bfa_comm', 'boundary4': 'NA'}
}
