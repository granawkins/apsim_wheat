from components.base_component import BaseComponent
from utils import interpolate

class Root(BaseComponent):

    def __init__(self, plant, parent=None):
        super().__init__(plant, parent)
        self.biomass_total = self.plant.vars['root_dm_init']
        self.root_length = 0
        self.root_senescence = 0

    def partition(self, available_biomass, env_conditions):
        root_ratio = interpolate(self.plant.phase_modifiers['x_stage_no_partition'],
                                 self.plant.phase_modifiers['y_ratio_root_shoot'],
                                 self.plant.stage)
        self.log('root_ratio', root_ratio)
        biomass_root = available_biomass * root_ratio
        self.biomass_total += biomass_root
        self.log('biomass_root', biomass_root)
        self.log('biomass_total', self.biomass())

        self.growth(biomass_root, env_conditions)
        self.senescence(biomass_root)

        return available_biomass - biomass_root

    def growth(self, biomass_root, env_conditions):
        # Root depth growth
        root_depth_growth_rate = interpolate(self.plant.phase_modifiers['stage_code_list'],
                                             self.plant.phase_modifiers['root_depth_rate'],
                                             self.plant.stage)
        temperature_factor = interpolate(self.plant.vars['x_temp_root_advance'],
                                         self.plant.vars['y_rel_root_advance'],
                                         env_conditions['air_temp_mean'])
        soil_water_stress_photosynthesis = 1
        soil_water_factor = interpolate(self.plant.vars['x_ws_root'],
                                        self.plant.vars['y_ws_root_fac'],
                                        soil_water_stress_photosynthesis)
        soil_water_available_factor = 1  # From soil module
        root_exploration_factor = 1      # From soil module
        root_depth_growth = root_depth_growth_rate * \
                            temperature_factor * \
                            min(soil_water_factor, soil_water_available_factor) * \
                            root_exploration_factor

        # Root length
        daily_root_length = biomass_root * self.plant.vars['specific_root_length']
        self.root_length += daily_root_length
        self.log('root_length', self.root_length)

    def senescence(self, biomass_root):
        root_senesced_fraction = self.root_senescence / self.biomass_total
        root_senescence_fraction = interpolate(self.plant.vars['x_dm_sen_frac_root'],
                                               self.plant.vars['y_dm_sen_frac_root'],
                                               root_senesced_fraction)
        root_senescence = biomass_root * root_senescence_fraction
        self.log('root_senescence', root_senescence)
        self.root_senescence += root_senescence

        # Root length - not calculated
