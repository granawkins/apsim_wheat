from components.base_component import BaseComponent
from utils import interpolate

class Stem(BaseComponent):

    def __init__(self, plant, parent=None):
        super().__init__(plant, parent)

        stem_biomass = self.plant.vars['stem_dm_init']
        self.biomass_total = stem_biomass
        structural_fraction = interpolate(self.plant.phase_modifiers['stemGrowthStructuralFractionStage'],
                                          self.plant.phase_modifiers['stemGrowthStructuralFraction'],
                                          self.plant.stage)
        self.biomass_structural = stem_biomass * structural_fraction
        self.biomass_non_structural = stem_biomass * (1 - structural_fraction)

    def partition(self, available_biomass):
        structural_fraction = interpolate(self.plant.phase_modifiers['stemGrowthStructuralFractionStage'],
                                          self.plant.phase_modifiers['stemGrowthStructuralFraction'],
                                          self.plant.stage)
        biomass_structural = available_biomass * structural_fraction
        self.biomass_structural += biomass_structural
        self.biomass_total += biomass_structural
        self.log('biomass_stem_structural', biomass_structural)

        biomass_non_structural = available_biomass - biomass_structural
        self.biomass_non_structural += biomass_non_structural
        self.biomass_total += biomass_non_structural
        self.log('biomass_stem_non_structural', biomass_non_structural)
        self.log('biomass_stem', biomass_structural + biomass_non_structural)

        self.log('biomass_total', self.biomass_total)

    def retranslocate_from(self, target):
        actual = min(target, self.biomass_non_structural * 0.2)
        self.biomass_non_structural -= actual
        self.biomass_total -= actual
        self.log('biomass_stem_retranslocated', actual)
        return actual

    def nitrogen_factor(self):
        nitrogen_concentration = 0.0001
        nitrogen_critical = interpolate(self.plant.phase_modifiers['x_stage_code'],
                                        self.plant.phase_modifiers['y_n_conc_crit_stem'],
                                        self.plant.stage)
        nitrogen_minimum = interpolate(self.plant.phase_modifiers['x_stage_code'],
                                       self.plant.phase_modifiers['y_n_conc_min_stem'],
                                       self.plant.stage)
        co2_factor = 1
        nitrogen_factor = (nitrogen_concentration - nitrogen_minimum) / ((nitrogen_critical * co2_factor) - nitrogen_minimum)
        self.log('stem_nitrogen_factor', nitrogen_factor)
        return nitrogen_factor
